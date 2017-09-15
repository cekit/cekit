# -*- coding: utf-8 -*-

import logging
import os
import subprocess

from jinja2 import Environment, FileSystemLoader

from concreate import tools
from concreate.descriptor import Descriptor
from concreate.errors import ConcreateError
from concreate.module import copy_module_to_target
from concreate.resource import Resource
from concreate.template_helper import TemplateHelper


logger = logging.getLogger('concreate')


class Generator(object):
    def __init__(self, descriptor_path, target, overrides):
        self.descriptor = Descriptor(descriptor_path, 'image').process()
        self.target = target
        self.effective_descriptor = self.descriptor
        if overrides:
            self.effective_descriptor = self.override(overrides)

        logger.info("Initializing image descriptor...")

    def prepare_modules(self, descriptor=None):
        """
        Prepare module to be used for Dockerfile generation.
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
            self.effective_descriptor.merge(descriptor)
            return

        logger.info("Handling modules...")

        for module in modules:
            version = None
            if 'version' in module:
                version = module['version']

            req_module = copy_module_to_target(module['name'],
                                               version,
                                               os.path.join(self.target, 'image', 'modules'))
            # If there is any required module it needs to be prepared too
            self.prepare_modules(req_module.descriptor)
            self.effective_descriptor.merge(descriptor)

        logger.debug("Modules handled")

    def fetch_artifacts(self):
        """ Goes through artifacts section of image descriptor
        and fetches all of them
        """
        if 'artifacts' not in self.descriptor:
            logger.debug("No artifacts to fetch")
            return
        logger.info("Handling artifacts...")
        target_dir = os.path.join(self.target, 'image')
        artifacts = self.descriptor['artifacts']
        for artifact in artifacts.values():
            artifact.copy(target_dir)
        logger.debug("Artifacts handled")

    def override(self, overrides_path):
        logger.info("Using overrides file from '%s'." % overrides_path)
        descriptor = Descriptor(overrides_path, 'overrides').process()
        descriptor.merge(self.effective_descriptor)
        return descriptor

    def render_dockerfile(self):
        """ Renders Dockerfile to $target/image/Dockerfile

        Args:
          template_file - a path to jinja2 template file
        """
        logger.info("Rendering Dockerfile...")
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
        with open(dockerfile, 'wb') as f:
            f.write(template.render(self.effective_descriptor.descriptor).encode('utf-8'))
        logger.debug("Dockerfile rendered")

    def prepare_repositories(self):
        """Udates descriptor with added repositories"""
        added_repos = []
        repo_file_urls = tools.cfg.get('repository', {}).get('urls', None)

        # If no repo files were defined or there are no packages to install,
        # skip handling additional repo files
        if not repo_file_urls or not self.effective_descriptor.get('packages'):
            return added_repos

        logger.info("Handling additional repository files...")
        target_dir = os.path.join(self.target, 'image', 'repos')
        os.makedirs(target_dir)

        for url in repo_file_urls.split(','):
            Resource.new({'url': url}).copy(target_dir)
            added_repos.append(os.path.splitext(os.path.basename(url))[0])

        self.descriptor['additional_repos'] = added_repos
        logger.debug("Additional repository files handled")

    def build(self):
        """
        After the source siles are generated, the container image can be built.
        We're using Docker to build the image currently.

        Built image will be avaialbe under two tags:

            1. version defined in the image descriptor
            2. 'latest'
        """
        # Desired tag of the image
        tag = "%s:%s" % (self.effective_descriptor['name'], self.effective_descriptor['version'])
        latest_tag = "%s:latest" % self.effective_descriptor['name']

        logger.info("Building %s container image..." % tag)

        ret = subprocess.call(["docker", "build", "-t", tag, "-t", latest_tag, os.path.join(self.target, 'image')])

        if ret == 0:
            logger.info("Image built and available under following tags: %s and %s" % (tag, latest_tag))
        else:
            raise ConcreateError("Image build failed, see logs above.")

