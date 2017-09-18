# -*- coding: utf-8 -*-

import argparse
import os
import logging
import sys

from concreate import tools
from concreate.log import setup_logging
from concreate.errors import ConcreateError
from concreate.generator import Generator
from concreate.module import discover_modules, get_dependencies
from concreate.version import version

# FIXME we shoudl try to move this to json
setup_logging()
logger = logging.getLogger('concreate')


class MyParser(argparse.ArgumentParser):

    def error(self, message):
        self.print_help()
        sys.stderr.write('\nError: %s\n' % message)
        sys.exit(2)


class Concreate(object):
    """ Main application """

    def run(self):
        parser = MyParser(
            description='Dockerfile generator tool',
            formatter_class=argparse.RawDescriptionHelpFormatter)

        parser.add_argument('-v',
                            '--verbose',
                            action='store_true',
                            help='verbose output')

        parser.add_argument('--version',
                            action='version',
                            help='show version and exit', version=version)

        parser.add_argument('--overrides',
                            help='path to a file containing overrides')

        parser.add_argument('--target',
                            default="target",
                            help="path to directory where to generate sources, \
                                default: 'target' directory in current working directory")

        parser.add_argument('--descriptor',
                            default="image.yaml",
                            help="path to image descriptor file, default: image.yaml")

        parser.add_argument('commands',
                            nargs='+',
                            choices=['generate', 'build'],
                            help="commands that should be executed, \
                                you can specify multiple commands")

        self.args = parser.parse_args()

        if self.args.verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        logger.debug("Running version %s", version)

        try:
            tools.cfg = tools.parse_cfg()
            tools.cleanup(self.args.target)

            # We need to construct Generator first, because we need overrides
            # merged in
            generator = Generator(self.args.descriptor,
                                  self.args.target,
                                  self.args.overrides)

            # Now we can fetch repositories of modules (we have all overrides)
            get_dependencies(generator.descriptor, os.path.join(self.args.target, 'repo'))

            # We have all overrided repo fetch so we can discover modules
            # and process its dependency trees
            discover_modules(os.path.join(self.args.target, 'repo'))

            if 'generate' in self.args.commands:
                # In case both: 'generate' and 'build' are specified
                # Make sure we only run generate once (as part of 'build')
                if 'build' not in self.args.commands:
                    self.generate(generator)

            if 'build' in self.args.commands:
                self.build(generator)

            logger.info("Finished!")
        except KeyboardInterrupt as e:
            pass
        except ConcreateError as e:
            if self.args.verbose:
                logger.exception(e)
            else:
                logger.error(str(e))
            sys.exit(1)

    def generate(self, generator):
        generator.prepare_artifacts()
        generator.prepare_modules()
        generator.prepare_repositories()
        generator.render_dockerfile()

    def build(self, generator):
        self.generate(generator)
        generator.build()


def run():
    Concreate().run()

if __name__ == "__main__":
    run()
