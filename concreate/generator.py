# -*- coding: utf-8 -*-

import logging
import os

from jinja2 import Environment, FileSystemLoader

from concreate import tools
from concreate.descriptor import Image, Overrides
from concreate.errors import ConcreateError
from concreate.module import copy_module_to_target
from concreate.resource import Resource
from concreate.template_helper import TemplateHelper


logger = logging.getLogger('concreate')


class Generator(object):

    def __init__(self, descriptor_path, target, overrides):

        self.descriptor = Image(tools.load_descriptor(descriptor_path),
                                os.path.dirname(descriptor_path))
        self.target = target

        if overrides:
            self.descriptor = self.override(overrides)

        logger.info("Initializing image descriptor...")

    def generate_tech_preview(self):
        name = self.descriptor.get('name')
        if '/' in name:
            family, name = name.split('/')
            self.descriptor['name'] = "%s-tech-preview/%s" % (family, name)
        else:
            self.descriptor['name'] = "%s-tech-preview" % name

    def get_tags(self):
        return ["%s:%s" % (self.descriptor['name'], self.descriptor[
            'version']), "%s:latest" % self.descriptor['name']]

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
            descriptor = self.descriptor

        modules = descriptor.get('modules', {}).get('install', {})

        # If descriptor doesn't requires any module we can start merging descriptors
        # and fetching artifacts. There is nothing left to do except for this
        if not modules:
            self.descriptor.merge(descriptor)
            return

        logger.info("Handling modules...")

        for module in modules:
            version = module.get('version', None)

            req_module = copy_module_to_target(module['name'],
                                               version,
                                               os.path.join(self.target, 'image', 'modules'))
            # If there is any required module it needs to be prepared too
            self.prepare_modules(req_module.descriptor)
            self.descriptor.merge(descriptor)

        logger.debug("Modules handled")

    def prepare_artifacts(self):
        """Goes through artifacts section of image descriptor
        and fetches all of them
        """
        if 'artifacts' not in self.descriptor:
            logger.debug("No artifacts to fetch")
            return

        logger.info("Handling artifacts...")
        target_dir = os.path.join(self.target, 'image')

        for artifact in self.descriptor['artifacts']:
            artifact.copy(target_dir)
        logger.debug("Artifacts handled")

    def override(self, overrides_path):
        logger.info("Using overrides file from '%s'." % overrides_path)
        descriptor = Overrides(tools.load_descriptor(overrides_path))
        descriptor.merge(self.descriptor)
        return descriptor

    def render_dockerfile(self):
        """Renders Dockerfile to $target/image/Dockerfile

        Args:
          template_file - a path to jinja2 template file
        """
        logger.info("Rendering Dockerfile...")

        self.descriptor.process_defaults()

        template_file = os.path.join(os.path.dirname(__file__),
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
                self.descriptor.descriptor).encode('utf-8'))
        logger.debug("Dockerfile rendered")

    def prepare_repositories(self):
        """Udates descriptor with added repositories"""
        configured_repositories = tools.cfg.get('repositories', {})

        # We need to remove the custom "__name__" element before we can show
        # which repository keys are defined in the configuration
        configured_repository_names = configured_repositories.keys()

        if '__name__' in configured_repository_names:
            configured_repository_names.remove('__name__')

        added_repos = []
        target_dir = os.path.join(self.target, 'image', 'repos')

        for repo in self.descriptor.get('packages', {}).get('repositories', []):
            if repo not in configured_repositories:
                raise ConcreateError("Package repository '%s' used in descriptor is not "
                                     "available in Concreate configuration file. "
                                     "Available repositories: %s"
                                     % (repo, configured_repository_names))

            urls = configured_repositories[repo]

            if urls:
                # we need to do this in this cycle to prevent creation of empty dir
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                logger.info("Handling additional repository files...")

                for url in urls.split(','):
                    Resource.new({'url': url}).copy(target_dir)
                    added_repos.append(os.path.splitext(
                        os.path.basename(url))[0])

                logger.debug("Additional repository files handled")

                self.descriptor['additional_repos'] = added_repos
