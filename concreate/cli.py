# -*- coding: utf-8 -*-

import argparse
import os
import logging
import sys


from concreate import tools
from concreate.builder import Builder
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

        build_group = parser.add_argument_group(
            'build', "Arguments valid for the 'build' target")

        build_group.add_argument('--build-engine',
                                 default='docker',
                                 choices=['docker', 'osbs'],
                                 help='an engine used to build the image.')

        build_group.add_argument('--build-tag',
                                 dest='build_tags',
                                 action='append',
                                 help='tag to assign to the built image, can be used multiple times')

        build_group.add_argument('--build-osbs-release',
                                 dest='build_osbs_release',
                                 action='store_true',
                                 default=False,
                                 help='execute OSBS release build.')

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
            get_dependencies(generator.descriptor,
                             os.path.join(self.args.target, 'repo'))

            # We have all overrided repo fetch so we can discover modules
            # and process its dependency trees
            discover_modules(os.path.join(self.args.target, 'repo'))

            # First we need to prepare a builder environment (it can change default target)
            if 'build' in self.args.commands:
                # we need to create the builder before generate, because it needs
                # to prepare env
                builder = Builder(self.args.build_engine, self.args.target)
                # build contains implicit generate
                self.args.commands.append('generate')

            if 'generate' in self.args.commands:
                generator.prepare_modules()
                generator.prepare_repositories()
                generator.prepare_artifacts()
                generator.render_dockerfile()

            if 'build' in self.args.commands:
                builder.prepare(generator.descriptor)
                if not self.args.build_tags:
                    self.args.build_tags = generator.get_tags()
                builder.build(self.args)

            logger.info("Finished!")
        except KeyboardInterrupt as e:
            pass
        except ConcreateError as e:
            if self.args.verbose:
                logger.exception(e)
            else:
                logger.error(str(e))
            sys.exit(1)


def run():
    Concreate().run()

if __name__ == "__main__":
    run()
