# -*- coding: utf-8 -*-

import logging
import os
import socket

from jinja2 import Environment, FileSystemLoader

from cekit import tools
from cekit.descriptor import Image, Overrides, Repository
from cekit.errors import CekitError
from cekit.module import copy_module_to_target
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
        self.target = target
        self._params = params
        self._fetch_repos = False

        if overrides:
            for override in overrides:
                self.image = self.override(override)

        logger.info("Initializing image descriptor...")

    def generate_tech_preview(self):
        """Appends '--tech-preview' to image name/family name"""
        name = self.image.get('name')
        if '/' in name:
            family, name = name.split('/')
            self.image['name'] = "%s-tech-preview/%s" % (family, name)
        else:
            self.image['name'] = "%s-tech-preview" % name

    def get_tags(self):
        return ["%s:%s" % (self.image['name'], self.image[
            'version']), "%s:latest" % self.image['name']]

    def prepare_modules(self, descriptor=None):
        """Prepare module to be used for Dockerfile generation.
        This means:

        1. Place module to args.target/image/modules/ directory
        2. Fetch its artifacts to target/image/sources directory
        3. Merge modules descriptor with image descriptor

        Arguments:
        descriptor: Module descriptor used to dig required modules,
            if descriptor is not provided image descriptor is used.
        """
        if not descriptor:
            descriptor = self.image

        modules = descriptor.get('modules', {}).get('install', [])[:]

        for module in reversed(modules):
            logger.debug("Preparing module '%s' requested by '%s'."
                         % (module['name'], descriptor['name']))
            version = module.get('version', None)

            req_module = copy_module_to_target(module['name'],
                                               version,
                                               os.path.join(self.target, 'image', 'modules'))

            self.prepare_modules(req_module)
            descriptor.merge(req_module)
            logger.debug("Merging '%s' module into '%s'." % (req_module['name'], descriptor['name']))

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

    def _inject_redhat_defaults(self):
        envs = [{'name': 'JBOSS_IMAGE_NAME',
                 'value': '%s' % self.image['name']},
                {'name': 'JBOSS_IMAGE_VERSION',
                 'value': '%s' % self.image['version']}]

        labels = [{'name': 'name',
                   'value': '%s' % self.image['name']},
                  {'name': 'version',
                   'value': '%s' % self.image['version']}]

        # do not override this label if it's already set
        if self.image.get('ports', []) and \
            'io.openshift.expose-services' not in [ k['name'] for k in self.image['labels'] ]:
            labels.append({'name': 'io.openshift.expose-services',
                           'value': self._generate_expose_services()})

        redhat_override = {'envs': envs,
                           'labels': labels}

        descriptor = Overrides(redhat_override, None)
        descriptor.merge(self.image)
        self.image = descriptor

    def render_dockerfile(self):
        """Renders Dockerfile to $target/image/Dockerfile"""
        logger.info("Rendering Dockerfile...")

        if self._params.get('redhat'):
            self._inject_redhat_defaults()

        self.image['pkg_manager'] = self._params.get('package_manager', 'yum')
        self.image.process_defaults()

        template_file = os.path.join(os.path.dirname(__file__),
                                     '..',
                                     'templates',
                                     'template.jinja')
        loader = FileSystemLoader(os.path.dirname(template_file))
        env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
        env.globals['helper'] = TemplateHelper()
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
        env.globals['helper'] = TemplateHelper()
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
