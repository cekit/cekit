# -*- coding: utf-8 -*-

import logging
import os

from jinja2 import Environment, FileSystemLoader

from cekit import tools
from cekit.descriptor import Image, Overrides
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

        if overrides:
            self.image = self.override(overrides)

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
        3. Merge modules descriptor with iamge descriptor

        Arguments:
        descriptor: Module descriptor used to dig required modules,
            if descriptor is not provided image descriptor is used.
        """
        if not descriptor:
            descriptor = self.image

        modules = descriptor.get('modules', {}).get('install', {})

        # If descriptor doesn't requires any module we can start merging descriptors
        # and fetching artifacts. There is nothing left to do except for this
        if not modules:
            self.image.merge(descriptor)
            return

        logger.info("Handling modules...")

        for module in modules:
            version = module.get('version', None)

            req_module = copy_module_to_target(module['name'],
                                               version,
                                               os.path.join(self.target, 'image', 'modules'))
            # If there is any required module it needs to be prepared too
            self.prepare_modules(req_module)
            self.image.merge(descriptor)

        logger.debug("Modules handled")

    def prepare_artifacts(self):
        """Goes through artifacts section of image descriptor
        and fetches all of them
        """
        if 'artifacts' not in self.image:
            logger.debug("No artifacts to fetch")
            return

        logger.info("Handling artifacts...")
        target_dir = os.path.join(self.target, 'image')

        for artifact in self.image['artifacts']:
            artifact.copy(target_dir)
        logger.debug("Artifacts handled")

    def override(self, overrides_path):
        logger.info("Using overrides file from '%s'." % overrides_path)
        descriptor = Overrides(tools.load_descriptor(overrides_path),
                               os.path.dirname(os.path.abspath(overrides_path)))
        descriptor.merge(self.image)
        return descriptor

    def _inject_redhat_defaults(self):
        envs = [{'name': 'JBOSS_IMAGE_NAME',
                 'value': '%s' % self.image['name']},
                {'name': 'JBOSS_IMAGE_VERSION',
                 'value': '%s' % self.image['version']}]

        labels = [{'name': 'name',
                   'value': '%s' % self.image['name']},
                  {'name': 'version',
                   'value': '%s' % self.image['version']},
                  {'name': 'architecture',
                   'value': "x86_64"}]

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

        self.image.process_defaults()

        template_file = os.path.join(os.path.dirname(__file__),
                                     '..',
                                     'templates',
                                     'template.jinja')
        loader = FileSystemLoader(os.path.dirname(template_file))
        env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
        env.globals['helper'] = TemplateHelper()
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

    def prepare_repositories(self):
        """ Prepare repositories for build time injection. """
        if 'packages' not in self.image:
            return

        repos = self.image.get('packages').get('repositories', [])

        injected_repos = []

        for repo in [x for x in repos if x.get('present')]:
            if self._handle_repository(repo):
                injected_repos.append(repo)

        for repo in injected_repos:
            repo.fetch(os.path.join(self.target, 'image', 'repos'))

        self.image['packages']['repositories_injected'] = injected_repos

    def _handle_repository(self, repo):
        """Process and prepares all v2 repositories.

        Args:
          repo a repository to process

        Returns True if repository file is prepared and should be injected"""

        logger.debug("Loading configuration for repository: '%s' from '%s'."
                     % (repo['name'],
                        'repositories-%s' % self._type))

        if 'odcs' in repo:
            if self._prepare_repository_odcs_pulp(repo):
                return True

        elif 'rpm' in repo:
            self._prepare_repository_rpm(repo)
            return False

        elif 'url' in repo:
            return True

        return False

    def _prepare_repository_odcs_pulp(self, repo, **kwargs):
        raise NotImplementedError("ODCS pulp repository injection not implemented!")

    def _prepare_repository_rpm(self, repo):
        raise NotImplementedError("RPM repository injection was not implemented!")
