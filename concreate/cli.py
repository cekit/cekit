# -*- coding: utf-8 -*-

import argparse
import os
import logging
import sys

from concreate import tools
from concreate.log import setup_logging
from concreate.errors import ConcreateError
from concreate.generator import Generator
from concreate.module import discover_modules, copy_modules_to_repository, get_dependencies
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

    def parse_args(self):
        parser = MyParser(
            description='Dockerfile generator tool',
            formatter_class=argparse.RawDescriptionHelpFormatter)

        parser.add_argument('-v',
                            '--verbose',
                            action='store_true',
                            help='Verbose output')

        parser.add_argument('--version',
                            action='version',
                            help='Show version and exit', version=version)

        parser.add_argument('--overrides',
                            help='Path to a file containing overrides.')

        parser.add_argument('descriptor_path',
                            help="Path to yaml descriptor to process")

        parser.add_argument('target',
                            help="Path to directory where generated files should be saved")

        self.args = parser.parse_args()
        return self

    def run(self):

        tools.Artifact.target_dir = os.path.join(self.args.target,
                                                 'image')

        if self.args.verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        logger.debug("Running version %s", version)
        try:
            tools.cfg = tools.parse_cfg()
            tools.cleanup(self.args.target)
            copy_modules_to_repository(
                os.path.join(os.path.dirname(self.args.descriptor_path),
                             'modules'),
                os.path.join(self.args.target,
                             'repo',
                             'modules'))

            # We need to construct Generator first, because we need overrides
            # merged in
            generator = Generator(self.args.descriptor_path,
                                  self.args.target,
                                  self.args.overrides)

            # Now we can fetch repositories of modules (we have all overrides)
            get_dependencies(generator.effective_descriptor, os.path.join(self.args.target,
                                                                          'repo'))

            # We have all overrided repo fetch so we can discover modules
            # and process its dependency trees
            discover_modules(os.path.join(self.args.target, 'repo'))

            generator.prepare_modules()
            generator.prepare_repositories()
            generator.render_dockerfile()
            generator.fetch_artifacts()
        except KeyboardInterrupt as e:
            pass
        except ConcreateError as e:
            if self.args.verbose:
                logger.exception(e)
            else:
                logger.error(str(e))
            sys.exit(1)


def run():
    Concreate().parse_args().run()

if __name__ == "__main__":
    run()
