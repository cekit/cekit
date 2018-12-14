#!/usr/bin/env python

import logging
import os
import yaml
import sys
from cekit.template_helper import TemplateHelper
from jinja2 import Environment, Template, FileSystemLoader

logger = logging.getLogger('cekit')

class Docgen():
    def __init__(self, descriptor='module.yaml'):
        # find module descriptor
        self.descriptor = descriptor
        if not os.path.isfile(self.descriptor):
            logger.error("Can't find module.yaml descriptor")
            sys.exit(1)
        logger.debug("Module descriptor path {} ".format(self.descriptor))

        # set up template path
        self.template_file = os.path.join(os.path.dirname(__file__),
                                          'templates',
                                          'module.adoc.jinja')
        logger.debug("Module doc template file {} ".format(self.template_file))

    def docgen(self):
        loader = FileSystemLoader(os.path.dirname(self.template_file))
        env = Environment(loader=loader)
        env.globals['helper'] = TemplateHelper()
        self.template = env.get_template(os.path.basename(self.template_file))
        self.generate_doc_for_module(self.descriptor)

    def generate_doc_for_module(self, module_file):
        with open(module_file) as open_file:
            data = yaml.load(open_file)
        output_file = os.path.join(os.path.dirname(module_file), 'README.adoc')
        logger.info("Generating %s..." % os.path.join(os.path.relpath(output_file, os.getcwd())), os.path.basename(output_file))
        with open(output_file, "w") as text_file:
            text_file.write(self.template.render(data))
