# -*- coding: utf-8 -*-

import logging
import os

from jinja2 import Environment, FileSystemLoader

from concreate import tools
from concreate.descriptor import Descriptor
from concreate.module import copy_module_to_target
from concreate.template_helper import TemplateHelper


logger = logging.getLogger('concreate')


class Generator(object):
    def __init__(self, descriptor_path, target, overrides):
        self.descriptor = Descriptor(descriptor_path, 'image').process()
        self.target = target
        self.effective_descriptor = self.descriptor
        if overrides:
            self.effective_descriptor = self.override(overrides)

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

        # If descriptor doesn't requires any module we can start merging descriptors
        # and fetching artifacts. There ibs nothing left to do except for this
        if 'modules' not in descriptor:
            self.effective_descriptor.merge(descriptor)
            return

        for module in descriptor['modules']:
            version = None
            if 'version' in module:
                version = module['version']

            req_module = copy_module_to_target(module['name'],
                                               version,
                                               os.path.join(self.target, 'image', 'modules'))
            # If there is any required module it needs to be prepared too
            self.prepare_modules(req_module.descriptor)
            self.effective_descriptor.merge(descriptor)

    def fetch_artifacts(self):
        """ Goes through artifacts section of image descriptor
        and fetches all of them
        """
        if 'artifacts' not in self.descriptor:
            return
        artifacts = self.descriptor['artifacts']
        for artifact_dict in artifacts:
            artifact = tools.Artifact(artifact_dict)
            artifact.fetch()
            artifact.verify()

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
        logger.debug("Done")

    def prepare_repositories(self):
        """Udates descriptor with added repositories"""
        self.descriptor['additional_repos'] = \
            tools.prepare_external_repositories(os.path.join(self.target,
                                                             'image'))
