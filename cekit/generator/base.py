# -*- coding: utf-8 -*-

import logging
import os
import shutil
import socket

from jinja2 import Environment, FileSystemLoader

from cekit import tools
from cekit.descriptor import Env, Image, Label, Module, Overrides, Repository
from cekit.errors import CekitError
from cekit.version import version as cekit_version
from cekit.template_helper import TemplateHelper

logger = logging.getLogger('cekit')


class Generator(object):
    """This class process Image descriptor(self.image) and uses it to generate
    target directory by fetching all dependencies and artifacts

    Args:
      descriptor_path - path to an image descriptor
      target - path to target directory
      builder - builder type
      overrides - path to overrides file (can be None)
      params - dictionary of builder specific parameterss
    """

    def __new__(cls, descriptor_path, target, builder, overrides, params):
        if cls is Generator:
            if 'docker' == builder or 'buildah' == builder:
                from cekit.generator.docker import DockerGenerator as GeneratorImpl
                logger.info('Generating files for %s engine.' % builder)
            elif 'osbs' == builder:
                from cekit.generator.osbs import OSBSGenerator as GeneratorImpl
                logger.info('Generating files for OSBS engine.')
            else:
                raise CekitError("Unsupported generator type: '%s'" % builder)
        return super(Generator, cls).__new__(GeneratorImpl)

    def __init__(self, descriptor_path, target, builder, overrides, params):
        self._type = builder
        descriptor = tools.load_descriptor(descriptor_path)

        # if there is a local modules directory and no modules are defined
        # we will inject it for a backward compatibility
        local_mod_path = os.path.join(os.path.abspath(os.path.dirname(descriptor_path)), 'modules')
        if os.path.exists(local_mod_path) and 'modules' in descriptor:
            modules = descriptor.get('modules')
            if not modules.get('repositories'):
                modules['repositories'] = [{'path': local_mod_path, 'name': 'modules'}]

        self.image = Image(descriptor, os.path.dirname(os.path.abspath(descriptor_path)))
        self._overrides = []
        self.target = target
        self._params = params
        self._fetch_repos = False
        self._module_registry = ModuleRegistry()

        if overrides:
            for override in overrides:
                logger.debug("Loading override '%s'" % (override))
                self._overrides.append(Overrides(tools.load_descriptor(override), os.path.dirname(os.path.abspath(override))))

        # These should always come last
        if self._params.get('tech_preview', False):
            # Modify the image name, after all other overrides have been processed
            self._overrides.append(self.get_tech_preview_overrides())
        if self._params.get('redhat', False):
            # Add the redhat specific stuff after everything else
            self._overrides.append(self.get_redhat_overrides())

        logger.info("Initializing image descriptor...")

    def init(self):
        """
        Initializes the generator.
        """
        self.process_image()
        self.image.process_defaults()
        self.copy_modules()

    def generate(self):
        self.prepare_repositories()
        self.image.remove_none_keys()
        self.image.write(os.path.join(self.target, 'image.yaml'))
        self.prepare_artifacts()
        self.render_dockerfile()

    def process_image(self):
        """
        Updates the image descriptor based on all overrides and included modules:
            1. Applies overrides to the image descriptor
            2. Loads modules from defined module repositories
            3. Flattens module dependency hierarchy
            4. Incorporates global image settings specified by modules into image descriptor
        The resulting image descriptor can be used in an 'offline' build mode.
        """
        # apply overrides to the image definition
        self.apply_image_overrides()
        # add build labels
        self.add_build_labels()
        # load the definitions of the modules
        self.build_module_registry()
        # process included modules
        self.apply_module_overrides()

    def apply_image_overrides(self):
        self.image.apply_image_overrides(self._overrides)

    def add_build_labels(self):
        image_labels = self.image.labels
        # we will persist cekit version in a label here, so we know which version of cekit
        # was used to build the image
        image_labels.extend([ Label({'name': 'org.concrt.version', 'value': cekit_version}),
                              Label({'name': 'io.cekit.version', 'value': cekit_version}) ])

        # If we define the label in the image descriptor
        # we should *not* override it with value from
        # the root's key
        if self.image.description and not self.image.label('description'):
            image_labels.append(Label({'name': 'description', 'value': self.image.description}))

        # Last - if there is no 'summary' label added to image descriptor
        # we should use the value of the 'description' key and create
        # a 'summary' label with it's content. If there is even that
        # key missing - we should not add anything.
        description = self.image.label('description')

        if not self.image.label('summary') and description:
            image_labels.append(Label({'name': 'summary', 'value': description['value']}))

    def apply_module_overrides(self):
        self.image.apply_module_overrides(self._module_registry)

    def build_module_registry(self):
        base_dir = os.path.join(self.target, 'repo')
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        for repo in self.image.modules.repositories:
            logger.debug("Downloading module repository: '%s'" % (repo.name))
            repo.copy(base_dir)
            self.load_repository(os.path.join(base_dir, repo.target_file_name()))

    def load_repository(self, repo_dir):
        for modules_dir, _, files in os.walk(repo_dir):
            if 'module.yaml' in files:
                module = Module(tools.load_descriptor(os.path.join(modules_dir, 'module.yaml')),
                                modules_dir,
                                os.path.dirname(os.path.abspath(os.path.join(modules_dir,
                                                                            'module.yaml'))))
                logger.debug("Adding module '%s', path: '%s'" % (module.name, module.path))
                self._module_registry.add_module(module)

    def get_tags(self):
        return ["%s:%s" % (self.image['name'], self.image[
            'version']), "%s:latest" % self.image['name']]

    def copy_modules(self):
        """Prepare module to be used for Dockerfile generation.
        This means:

        1. Place module to args.target/image/modules/ directory

        """
        target = os.path.join(self.target, 'image', 'modules')
        for module in self.image.modules.install:
            module = self._module_registry.get_module(module.name, module.version)
            logger.debug("Copying module '%s' required by '%s'."
                         % (module.name, self.image.name))

            dest = os.path.join(target, module.name)

            if not os.path.exists(dest):
                logger.debug("Copying module '%s' to: '%s'" % (module.name, dest))
                shutil.copytree(module.path, dest)
            # write out the module with any overrides
            module.write(os.path.join(dest, "module.yaml"))

    def override(self, overrides_path):
        logger.info("Using overrides file from '%s'." % overrides_path)
        descriptor = Overrides(tools.load_descriptor(overrides_path),
                               os.path.dirname(os.path.abspath(overrides_path)))
        descriptor.merge(self.image)
        return descriptor

    def _generate_expose_services(self):
        """Generate the label io.openshift.expose-services based on the port
        definitions."""
        ports = []
        for p in self.image['ports']:
            if p.get('expose', True):

                r = "{}/{}".format(p['value'], p.get('protocol', 'tcp'))

                if 'service' in p:
                    r += ":{}".format(p['service'])
                    ports.append(r)
                else:
                    # attempt to supply a service name by looking up the socket number
                    try:
                        service = socket.getservbyport(p['value'], p.get('protocol','tcp'))
                        r += ":{}".format(service)
                        ports.append(r)

                    except OSError: # py3
                        pass
                    except socket.error: # py2
                        pass

        return ",".join(ports)

    def get_tech_preview_overrides(self):
        class TechPreviewOverrides(Overrides):
            def __init__(self, image):
                super(TechPreviewOverrides, self).__init__({}, None)
                self._image = image

            @property
            def name(self):
                new_name = self._image.name
                if '/' in new_name:
                    family, new_name = new_name.split('/')
                    new_name = "%s-tech-preview/%s" % (family, new_name)
                else:
                    new_name = "%s-tech-preview" % new_name
                return new_name

        return TechPreviewOverrides(self.image)

    def get_redhat_overrides(self):
        class RedHatOverrides(Overrides):
            def __init__(self, generator):
                super(RedHatOverrides, self).__init__({}, None)
                self._generator = generator

            @property
            def envs(self):
                return [
                        Env({'name': 'JBOSS_IMAGE_NAME', 'value': '%s' % self._generator.image['name']}),
                        Env ({'name': 'JBOSS_IMAGE_VERSION', 'value': '%s' % self._generator.image['version']})
                    ]

            @property
            def labels(self):
                labels = [
                        Label({'name': 'name', 'value': '%s' % self._generator.image['name']}),
                        Label({'name': 'version', 'value': '%s' % self._generator.image['version']})
                    ]

                # do not override this label if it's already set
                if self._generator.image.get('ports', []) and \
                    'io.openshift.expose-services' not in [ k['name'] for k in self._generator.image['labels'] ]:
                    labels.append(Label({'name': 'io.openshift.expose-services',
                                'value': self._generator._generate_expose_services()}))

                return labels

        return RedHatOverrides(self)

    def render_dockerfile(self):
        """Renders Dockerfile to $target/image/Dockerfile"""
        logger.info("Rendering Dockerfile...")

        self.image['pkg_manager'] = self._params.get('package_manager', 'yum')

        template_file = os.path.join(os.path.dirname(__file__),
                                     '..',
                                     'templates',
                                     'template.jinja')
        loader = FileSystemLoader(os.path.dirname(template_file))
        env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
        env.globals['helper'] = TemplateHelper(self._module_registry)
        env.globals['image'] = self.image
        env.globals['addhelp'] = self._params.get('addhelp')

        template = env.get_template(os.path.basename(template_file))

        dockerfile = os.path.join(self.target,
                                  'image',
                                  'Dockerfile')
        if not os.path.exists(os.path.dirname(dockerfile)):
            os.makedirs(os.path.dirname(dockerfile))

        with open(dockerfile, 'wb') as f:
            f.write(template.render(
                self.image).encode('utf-8'))
        logger.debug("Dockerfile rendered")

        if self.image.get('help', {}).get('template', ""):
            help_template_path = self.image['help']['template']
        elif self._params.get('help_template'):
            help_template_path = self._params['help_template']
        else:
            help_template_path = os.path.join(os.path.dirname(__file__),
                                              '..',
                                              'templates',
                                              'help.jinja')

        help_dirname, help_basename = os.path.split(help_template_path)
        loader = FileSystemLoader(help_dirname)
        env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
        env.globals['helper'] = TemplateHelper(self._module_registry)
        help_template = env.get_template(help_basename)

        helpfile = os.path.join(self.target, 'image', 'help.md')
        with open(helpfile, 'wb') as f:
            f.write(help_template.render(
                self.image).encode('utf-8'))
        logger.debug("help.md rendered")

    def prepare_repositories(self):
        """ Prepare repositories for build time injection. """
        if 'packages' not in self.image:
            return

        if self.image.get('packages').get('content_sets'):
            logger.warning('The image has ContentSets repositories specified, all other repositories are removed!')
            self.image['packages']['repositories'] = []
        repos = self.image.get('packages').get('repositories', [])

        injected_repos = []

        for repo in repos:
            if self._handle_repository(repo):
                injected_repos.append(repo)

        if self.image.get('packages').get('content_sets'):
            url = self._prepare_content_sets(self.image.get('packages').get('content_sets'))
            if url:
                repo = Repository({'name': 'content_sets_odcs',
                                   'url': {'repository': url}})
                injected_repos.append(repo)
                self._fetch_repos = True

        if self._fetch_repos:
            for repo in injected_repos:
                repo.fetch(os.path.join(self.target, 'image', 'repos'))
            self.image['packages']['repositories_injected'] = injected_repos
        else:
            self.image['packages']['set_url'] = injected_repos

    def _handle_repository(self, repo):
        """Process and prepares all v2 repositories.

        Args:
          repo a repository to process

        Returns True if repository file is prepared and should be injected"""

        logger.debug("Loading configuration for repository: '%s' from '%s'."
                     % (repo['name'],
                        'repositories-%s' % self._type))

        if 'id' in repo:
            logger.warning("Repository '%s' is defined as plain. It must be available "
                           "inside the image as Cekit will not inject it."
                           % repo['name'])
            return False

        if 'content_sets' in repo:
            self._fetch_repos = True
            return self._prepare_content_sets(repo)

        elif 'rpm' in repo:
            self._prepare_repository_rpm(repo)
            return False

        elif 'url' in repo:
            return True

        return False

    def _prepare_content_sets(self, content_sets):
        raise NotImplementedError("Content sets repository injection not implemented!")

    def _prepare_repository_rpm(self, repo):
        raise NotImplementedError("RPM repository injection was not implemented!")

    def prepare_artifacts(self):
        raise NotImplementedError("Artifacts handling is not implemented")

class ModuleRegistry(object):
    def __init__(self):
        self._modules = {}

    def get_module(self, name, version=None):
        versions = self._modules.get(name, {})
        if version == None:
            default = versions.get('default')
            if len(versions) > 2: # we always add the first seen as 'default'
                logger.warning("Module version not specified for %s, using %s version." % (name, default.version))
            return default
        return versions.get(version, None)

    def add_module(self, module):
        versions = self._modules.get(module.name)
        if not versions:
            versions = {}
            self._modules[module.name] = versions
        version = module.version
        if not version:
            version = 'None'
        existing = versions.get(version, None)
        if existing:
            raise CekitError("Duplicate module (%s:%s) found while processing module repository"
                             % (module.name, module.version))
        if len(versions) == 0:
            # for better or worse...
            versions['default'] = module
        versions[version] = module
