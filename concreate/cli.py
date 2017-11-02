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
from concreate.test.collector import TestCollector
from concreate.test.runner import TestRunner
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

    def parse(self):
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

        test_group = parser.add_argument_group('test',
                                               "Arguments valid for the 'test' target")

        test_group.add_argument('--test-wip',
                                action='store_true',
                                help='Run @wip tests only')

        build_group = parser.add_argument_group('build',
                                                "Arguments valid for the 'build' target")

        build_group.add_argument('--build-engine',
                                 default='docker',
                                 choices=['docker', 'osbs'],
                                 help='an engine used to build the image.')

        build_group.add_argument('--build-tag',
                                 dest='build_tags',
                                 action='append',
                                 help='tag to assign to the built image, can be used multiple times')

        build_group.add_argument('--tag',
                                 dest='tags',
                                 action='append',
                                 help='tag used to build/test the image, can be used multiple times')

        build_group.add_argument('--build-osbs-release',
                                 dest='build_osbs_release',
                                 action='store_true',
                                 help='execute OSBS release build')

        build_group.add_argument('--build-tech-preview',
                                 action='store_true',
                                 help='perform tech preview build')

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
                            choices=['generate', 'build', 'test'],
                            help="commands that should be executed, \
                                you can specify multiple commands")

        self.args = parser.parse_args()

        # DEPRECATED - remove following lines and --build-tag option
        if self.args.build_tags:
            logger.warning("--build-tag is deprecated and will be removed in concreate 2.0, please use --tag instead.")
            if not self.args.tags:
                self.args.tags = self.args.build_tags
            else:
                self.args.tags += self.args.build_tags

        return self

    def run(self):
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

            # we run generate for every possible command
            if self.args.commands:
                generator.prepare_modules()
                generator.prepare_repositories()
                generator.prepare_artifacts()
                if self.args.build_tech_preview:
                    generator.generate_tech_preview()
                generator.descriptor.write(os.path.join(self.args.target, 'image.yaml'))
                generator.render_dockerfile()

                # if tags are not specified on command line we take them from image descriptor
                if not self.args.tags:
                    self.args.tags = generator.get_tags()

            if 'build' in self.args.commands:
                builder = Builder(self.args.build_engine, self.args.target)
                builder.prepare(generator.descriptor)
                builder.build(self.args)

            if 'test' in self.args.commands:

                test_tags = [generator.get_tags()[0]]
                # if wip is specifed set tags to @wip
                if self.args.test_wip:
                    test_tags = ['@wip']

                # at first we collect tests
                test_collected = TestCollector(os.path.dirname(self.args.descriptor),
                                               self.args.target).collect(generator.descriptor.get('schema_version'))

                # we run the test only if we collect any
                if test_collected:
                    TestRunner(self.args.target).run(self.args.tags[0],
                                                     test_tags)

            logger.info("Finished!")
            sys.exit(0)
        except KeyboardInterrupt as e:
            pass
        except ConcreateError as e:
            if self.args.verbose:
                logger.exception(e)
            else:
                logger.error(str(e))
            sys.exit(1)


def run():
    Concreate().parse().run()

if __name__ == "__main__":
    run()
