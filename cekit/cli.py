# -*- coding: utf-8 -*-

import argparse
import os
import logging
import sys


from cekit import tools
from cekit.builder import Builder
from cekit.log import setup_logging
from cekit.errors import CekitError
from cekit.generator.base import Generator
from cekit.module import discover_modules, get_dependencies
from cekit.test.collector import TestCollector
from cekit.test.runner import TestRunner
from cekit.version import version

# FIXME we shoudl try to move this to json
setup_logging()
logger = logging.getLogger('cekit')


class MyParser(argparse.ArgumentParser):

    def error(self, message):
        self.print_help()
        sys.stderr.write('\nError: %s\n' % message)
        sys.exit(2)


class Cekit(object):
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

        parser.add_argument('--config',
                            default='~/.cekit/config',
                            help='path for cekit config file (~/.cekit/config is default)')

        parser.add_argument('--redhat',
                            action='store_true',
                            help='Set default options for Red Hat internal infrasructure.')

        parser.add_argument('--work-dir',
                            dest='work_dir',
                            help="Location of cekit working directory, it's "
                            "used to store dist-git repos.")

        test_group = parser.add_argument_group('test',
                                               "Arguments valid for the 'test' target")

        test_group.add_argument('--test-wip',
                                action='store_true',
                                help='Run @wip tests only')

        steps_url = 'https://github.com/cekit/behave-test-steps.git'
        test_group.add_argument('--test-steps-url',
                                default=steps_url,
                                help='contains url for cekit test stesp')

        build_group = parser.add_argument_group('build',
                                                "Arguments valid for the 'build' target")

        build_group.add_argument('--build-engine',
                                 default='docker',
                                 choices=['docker', 'osbs', 'buildah'],
                                 help='an engine used to build the image.')

        build_group.add_argument('--build-tag',
                                 dest='build_tags',
                                 action='append',
                                 help='tag to assign to the built image, '
                                 'can be used multiple times')

        build_group.add_argument('--build-pull',
                                 dest='build_pull',
                                 action='store_true',
                                 help='Always fetch latest base image during build')

        build_group.add_argument('--build-osbs-release',
                                 dest='build_osbs_release',
                                 action='store_true',
                                 help='execute OSBS release build')

        build_group.add_argument('--build-osbs-user',
                                 dest='build_osbs_user',
                                 help='user for rphkg tool')

        build_group.add_argument('--build-osbs-nowait',
                                 dest='build_osbs_nowait',
                                 action='store_true',
                                 help='run rhpkg container build with --nowait option')

        build_group.add_argument('--build-osbs-stage',
                                 dest='build_osbs_stage',
                                 action='store_true',
                                 help='use rhpkg-stage instead of rhpkg')

        build_group.add_argument('--build-osbs-target',
                                 dest='build_osbs_target',
                                 help='overrides the default rhpkg target')

        build_group.add_argument('--build-tech-preview',
                                 action='store_true',
                                 help='perform tech preview build')

        parser.add_argument('--tag',
                            dest='tags',
                            action='append',
                            help='tag used to build/test the image, can be used multiple times')

        overrides_group = parser.add_mutually_exclusive_group()

        overrides_group.add_argument('--overrides',
                                     help='a YAML object to override image descriptor')

        overrides_group.add_argument('--overrides-file',
                                     dest='overrides',
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
            logger.warning("--build-tag is deprecated and will be removed in cekit 2.0,"
                           " please use --tag instead.")
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
        if 'dev' in version:
            logger.warning("You are running unreleased development version of Cekit, "
                           "use it only at your own risk!")

        try:
            tools.cfg = tools.get_cfg(self.args.config)
            tools.cleanup(self.args.target)

            if self.args.redhat:
                tools.cfg['common']['redhat'] = True
            if self.args.work_dir:
                tools.cfg['common']['work_dir'] = self.args.work_dir

            # We need to construct Generator first, because we need overrides
            # merged in
            params = {'redhat': tools.cfg['common']['redhat']}
            generator = Generator(self.args.descriptor,
                                  self.args.target,
                                  self.args.build_engine,
                                  self.args.overrides,
                                  params)

            # Now we can fetch repositories of modules (we have all overrides)
            get_dependencies(generator.image,
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
                generator.image.write(os.path.join(self.args.target, 'image.yaml'))
                generator.render_dockerfile()

                # if tags are not specified on command line we take them from image descriptor
                if not self.args.tags:
                    self.args.tags = generator.get_tags()

            if 'build' in self.args.commands:
                params = {'user': self.args.build_osbs_user,
                          'nowait': self.args.build_osbs_nowait,
                          'stage': self.args.build_osbs_stage,
                          'release': self.args.build_osbs_release,
                          'tags': self.args.tags,
                          'pull': self.args.build_pull,
                          'redhat': tools.cfg['common']['redhat'],
                          'target': self.args.build_osbs_target
                          }

                builder = Builder(self.args.build_engine,
                                  self.args.target,
                                  params)
                builder.prepare(generator.image)
                builder.build()

            if 'test' in self.args.commands:

                test_tags = [generator.get_tags()[0]]
                # if wip is specifed set tags to @wip
                if self.args.test_wip:
                    test_tags = ['@wip']

                # at first we collect tests
                tc = TestCollector(os.path.dirname(self.args.descriptor),
                                   self.args.target)

                # we run the test only if we collect any
                if tc.collect(generator.image.get('schema_version'), self.args.test_steps_url):
                    runner = TestRunner(self.args.target)
                    runner.run(self.args.tags[0], test_tags)
                else:
                    logger.warning("No test collected, test can't be run.")

            logger.info("Finished!")
            sys.exit(0)
        except KeyboardInterrupt as e:
            pass
        except CekitError as e:
            if self.args.verbose:
                logger.exception(e)
            else:
                logger.error(str(e))
            sys.exit(1)


def run():
    Cekit().parse().run()


if __name__ == "__main__":
    run()
