# -*- coding: utf-8 -*-

import argparse
import os
import logging
import sys


from cekit.config import Config
from cekit.builder import Builder
from cekit.log import setup_logging
from cekit.errors import CekitError
from cekit.generator.base import Generator
from cekit.module import discover_modules, get_dependencies
from cekit.test.collector import TestCollector
from cekit.test.runner import TestRunner
from cekit.tools import cleanup
from cekit.version import version

# FIXME we shoudl try to move this to json
setup_logging()
logger = logging.getLogger('cekit')
config = Config()

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
                            help='path for Cekit config file (~/.cekit/config is default)')

        parser.add_argument('--redhat',
                            action='store_true',
                            help='Set default options for Red Hat internal infrasructure.')

        parser.add_argument('--work-dir',
                            dest='work_dir',
                            help="Location of Cekit working directory.")

        parser.add_argument('--package-manager',
                            dest='package_manager',
                            choices=['yum', 'microdnf'],
                            help='Package manager to use. Supports yum and microdnf, \
                                defaults: yum')

        test_group = parser.add_argument_group('test',
                                               "Arguments valid for the 'test' target")

        limit_test_group = test_group.add_mutually_exclusive_group()

        steps_url = 'https://github.com/cekit/behave-test-steps.git'
        test_group.add_argument('--test-steps-url',
                                default=steps_url,
                                help='contains url for cekit test steps')

        limit_test_group.add_argument('--test-wip',
                                      action='store_true',
                                      help='Run @wip tests only')

        limit_test_group.add_argument('--test-name',
                                      dest='test_names',
                                      action='append',
                                      help='Name of the Scenario to be executed')

        build_group = parser.add_argument_group('build',
                                                "Arguments valid for the 'build' target")

        build_group.add_argument('--build-engine',
                                 default='docker',
                                 choices=['docker', 'osbs', 'buildah'],
                                 help='an engine used to build the image.')

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

        build_group.add_argument('--build-osbs-commit-msg',
                                 dest='build_osbs_commit_msg',
                                 help='commit message for dist-git')

        build_group.add_argument('--build-tech-preview',
                                 action='store_true',
                                 help='perform tech preview build')

        parser.add_argument('--tag',
                            dest='tags',
                            action='append',
                            help='tag used to build/test the image, can be used multiple times')

        parser.add_argument('--overrides',
                            action='append',
                            help='a YAML object to override image descriptor')

        parser.add_argument('--overrides-file',
                            action='append',
                            dest='overrides',
                            help='path to a file containing overrides')

        parser.add_argument('--target',
                            default="target",
                            help="path to directory where to generate sources, \
                                default: 'target' directory in current working directory")

        parser.add_argument('--descriptor',
                            default="image.yaml",
                            help="path to image descriptor file, default: image.yaml")

        addhelp_group = parser.add_mutually_exclusive_group()

        addhelp_group.add_argument('--add-help',
                                   dest='addhelp',
                                   action='store_const',
                                   const=True,
                                   help="Include generate help files in the image")

        addhelp_group.add_argument('--no-add-help',
                                   dest='addhelp',
                                   action='store_const',
                                   const=False,
                                   help="Do not include generate help files in the image")

        parser.add_argument('commands',
                            nargs='+',
                            choices=['generate', 'build', 'test'],
                            help="commands that should be executed, \
                                you can specify multiple commands")

        self.args = parser.parse_args()

        return self

    def configure(self):
        if self.args.verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        logger.debug("Running version %s", version)
        if 'dev' in version or 'rc' in version:
            logger.warning("You are running unreleased development version of Cekit, "
                           "use it only at your own risk!")

        config.configure(self.args.config, {'redhat': self.args.redhat,
                                            'work_dir': self.args.work_dir,
                                            'addhelp': self.args.addhelp,
                                            'package_manager': self.args.package_manager})

        cleanup(self.args.target)

        # We need to construct Generator first, because we need overrides
        # merged in
        params = {
            'addhelp': config.get('doc', 'addhelp'),
            'redhat':  config.get('common', 'redhat'),
            'help_template': config.get('doc', 'help_template'),
            'package_manager': config.get('common', 'package_manager')
        }

        self.generator = Generator(self.args.descriptor,
                                   self.args.target,
                                   self.args.build_engine,
                                   self.args.overrides,
                                   params)

    def run(self):

        try:
            self.configure()
            generator = self.generator

            # Now we can fetch repositories of modules (we have all overrides)
            get_dependencies(generator.image,
                             os.path.join(self.args.target, 'repo'))

            # We have all overrided repo fetch so we can discover modules
            # and process its dependency trees
            discover_modules(os.path.join(self.args.target, 'repo'))
            generator.prepare_modules()
            if self.args.build_tech_preview:
                generator.generate_tech_preview()

            # if tags are not specified on command line we take them from image descriptor
            if not self.args.tags:
                self.args.tags = generator.get_tags()

            # we run generate for build command too
            if set(['generate', 'build']).intersection(set(self.args.commands)):
                generator.prepare_repositories()
                generator.image.remove_none_keys()
                generator.prepare_artifacts()
                generator.image.write(os.path.join(self.args.target, 'image.yaml'))
                generator.render_dockerfile()

            if 'build' in self.args.commands:
                params = {'user': self.args.build_osbs_user,
                          'nowait': self.args.build_osbs_nowait,
                          'stage': self.args.build_osbs_stage,
                          'release': self.args.build_osbs_release,
                          'tags': self.args.tags,
                          'pull': self.args.build_pull,
                          'redhat': config.get('common', 'redhat'),
                          'target': self.args.build_osbs_target,
                          'commit_msg': self.args.build_osbs_commit_msg
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
                    runner.run(self.args.tags[0], test_tags, test_names=self.args.test_names)
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
                logger.error(e.message)
            sys.exit(1)


def run():
    Cekit().parse().run()


if __name__ == "__main__":
    run()
