# -*- coding: utf-8 -*-

import click
import logging
import os
import sys

from cekit.builder import Builder
from cekit.config import Config
from cekit.errors import CekitError
from cekit.generator.base import Generator
from cekit.log import setup_logging
from cekit.test.collector import TestCollector
from cekit.test.runner import TestRunner
from cekit.tools import DependencyHandler, Map, cleanup
from cekit.version import version

# FIXME we should try to move this to json
setup_logging()
logger = logging.getLogger('cekit')
config = Config()


@click.group(context_settings=dict(max_content_width=100))
@click.option('--descriptor', metavar="PATH", help="Path to image descriptor file.", default="image.yaml", show_default=True)
@click.option('-v', '--verbose', help="Enable verbose output.", is_flag=True)
@click.option('--work-dir', help="Location of the working directory.", default="~/.cekit", show_default=True)
@click.option('--config', metavar="PATH", help="Path to configuration file.", default="~/.cekit/config", show_default=True)
@click.option('--redhat', help="Set default options for Red Hat internal infrastructure.", is_flag=True)
@click.option('--target', metavar="PATH", help="Path to directory where files should be generated", default="target", show_default=True)
# TODO: Remove this option
@click.option('--package-manager', help="Package manager to use.", type=click.Choice(['yum', 'microdnf']), default="yum", show_default=True)
@click.version_option(message="%(version)s", version=version)
def cli(descriptor, verbose, work_dir, config, redhat, target, package_manager):
    """
    ABOUT

        CEKit -- container image creation tool

    LINKS

    \b
        Website: https://cekit.io/
        Documentation: https://docs.cekit.io/
        Issue tracker: https://github.com/cekit/cekit/issues

    EXAMPLES

        Build container image in Docker

            $ cekit build docker

        Execute tests for the example/app:1.0 image

            $ cekit test example/app:1.0
    """
    pass


@cli.group(short_help="Build container image")
@click.option('--dry-run', help="Do not execute the build, just generate required files.", is_flag=True)
@click.option('--overrides', metavar="JSON", help="Inline overrides in JSON format.", multiple=True)
@click.option('--overrides-file', 'overrides', metavar="PATH", help="Path to overrides file in YAML format.", multiple=True)
# TODO: Is this ok?
@click.option('--add-help', 'addhelp', help="Include generated help files in the image.", type=click.BOOL)
def build(dry_run, overrides, addhelp):
    """
    DESCRIPTION

        Executes container image build using selected builder.

    BUILDERS

        We currently support: Docker, OSBS and Buildah.

            $ cekit build BUILDER

        See commands cor the proper invocation.

    OVERRIDES

        You can specify overrides to modify the container image build. You can read more about overrides in the documentation: https://docs.cekit.io/en/latest/overrides.html.

        Overrides can be specified inline (--overrides) or as a path to file (--overrides-file).

        Overrides can be specified multiple times.

        Please note that order matters; overrides on the right hand side take precedence! For example:

            $ cekit build --overrides '{"from": "custom/image:1.0"}' --overrides '{"from": "custom/image:2.0"}'

        Will change the 'from' key in the descriptor to 'custom/image:2.0'.

    """
    pass


@build.command(name="docker", short_help="Build using Docker engine")
@click.option('--pull', help="Always try to fetch latest base image.", is_flag=True)
@click.option('--no-squash', help="Do not squash the image after build is done.", is_flag=True)
@click.option('--tag', 'tags', metavar="TAG", help="Tag the image after build, can be specified multiple times.", multiple=True)
def build_docker(pull, no_squash, tags):
    """
    DESCRIPTION

        Executes container image build locally using Docker builder.

        https://docs.docker.com/
    """
    run()


@build.command(name="buildah", short_help="Build using Buildah engine")
@click.option('--pull', help="Always try to fetch latest base image.", is_flag=True)
@click.option('--tag', 'tags', metavar="TAG", help="Tag the image after build, can be used specified times.", multiple=True)
def build_buildah(pull, tags):
    """
    DESCRIPTION

        Executes container image build locally using Buildah builder.

        https://buildah.io/
    """
    run()


@build.command(name="osbs", short_help="Build using OSBS engine")
@click.option('--release', help="Execute a release build.", is_flag=True)
# TODO: Ensure this still makes sense
@click.option('--tech-preview', help="Execute a tech preview build.", is_flag=True)
@click.option('--user', metavar="USER", help="User used to kick the build as.")
@click.option('--nowait', help="Do not wait for the task to finish.", is_flag=True)
@click.option('--stage', help="Use stage environmen.", is_flag=True)
@click.option('--target', metavar="TARGET", help="Override the default target.")
@click.option('--commit-message', metavar="MESSAGE", help="Custom dist-git commit message.")
def build_osbs(release, tech_preview, user, nowait, stage, target, commit_message):
    """
    DESCRIPTION

        Executes container image build using OSBS builder.

        https://osbs.readthedocs.io
    """
    run()


@cli.command(short_help="Execute container image tests")
@click.option('--steps-url', help="Behave steps library.", default='https://github.com/cekit/behave-test-steps.git', show_default=True)
@click.option('--wip', help="Run test scenarios tagged with @wip only.", is_flag=True)
@click.option('--name', 'names', help="Run test scenario with the specified name, can be used specified times.", multiple=True)
@click.argument('image')
def test(steps_url, wip, names, image):
    """
    DESCRIPTION

        Execute container image tests locally using Docker

        NOTE: Image to test must be available in the Docker daemon. It won't be pulled automatically!

    EXAMPLES

        Execute tests for the example/app:1.0 image

            $ cekit test example/app:1.0

        Execute tests that are currently developed and marked with @wip

            $ cekit test --wip example/app:1.0

        Execute specific scenario

            $ cekit test --name 'Check that product labels are correctly set' example/app:1.0
    """

    if wip and names:
        raise click.UsageError("Parameters --name and --wip cannot be used together")

    run()


def _cli_context_hierarchy(ctx, hierarchy=None):
    if hierarchy is None:
        hierarchy = []

    if ctx.parent:
        _cli_context_hierarchy(ctx.parent, hierarchy)

    hierarchy.append(ctx)

    return hierarchy


def run():
    contexts = _cli_context_hierarchy(click.get_current_context())
    commands = []
    params = {}

    for context in contexts:
        commands.append(context.command.name)
        params.update(context.params)

    # Remove the default 'cli' command
    # Conditional here to make tests work better
    if 'cli' in commands:
        commands.remove('cli')

    # return Map({'commands': commands, 'params': Map(params)})

    Cekit(commands, Map(params)).run()


class Cekit(object):
    """ Main application """

    def __init__(self, commands, args):
        self.cli_commands = commands
        self.cli_args = args

    def _configure(self, args):

        config.configure(args.config, {'redhat': args.redhat,
                                       'work_dir': args.work_dir,
                                       'addhelp': args.addhelp,
                                       'package_manager': args.package_manager})

    def run(self):
        if self.cli_args.verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        logger.debug("Running version %s", version)

        if 'dev' in version or 'rc' in version:
            logger.warning("You are running unreleased development version of CEKit, "
                           "use it only at your own risk!")

        # Initialize dependency handler
        dependency_handler = DependencyHandler()

        logger.debug("Checking CEKit core dependencies...")
        dependency_handler.handle_core_dependencies()

        self._configure(self.cli_args)

        # Cleanup the target directory
        cleanup(self.cli_args.target)

        params = {
            'redhat':  config.get('common', 'redhat'),
            # TODO: https://github.com/cekit/cekit/issues/377
            'addhelp': config.get('doc', 'addhelp'),
            'help_template': config.get('doc', 'help_template'),
            # TODO: Remove it from here: https://github.com/cekit/cekit/issues/400
            'package_manager': config.get('common', 'package_manager'),
            'tech_preview': self.cli_args.build_tech_preview
        }

        try:
            # we run generate for build command too
            if 'build' in self.cli_commands:
                # TODO: When executing tests, we should not initialize generator at all
                # If the 'build' command is specified,
                # then the builder type is the last argument
                self.generator = Generator(self.cli_args.descriptor,
                                           self.cli_args.target,
                                           self.cli_commands[-1],
                                           self.cli_args.overrides,
                                           params)

                # Handle dependencies for selected generator, if any
                logger.debug("Checking CEKit generate dependencies...")
                dependency_handler.handle(self.generator)

                self.generator.init()
                self.generator.generate()

                # If --dry-run is specified, do not execute the build
                if self.cli_args.dry_run:
                    logger.info("The --dry-run parameter was specified, build will not be executed")
                    logger.info("Finished!")
                    sys.exit(0)
                    return

                # If tags are not specified on command line we take them from image descriptor
                if not self.cli_args.tags:
                    self.cli_args.tags = self.generator.get_tags()

                params = {'user': self.cli_args.build_osbs_user,
                          'nowait': self.cli_args.build_osbs_nowait,
                          'stage': self.cli_args.build_osbs_stage,
                          'release': self.cli_args.build_osbs_release,
                          'no_squash': self.cli_args.build_docker_no_squash,
                          'tags': self.cli_args.tags,
                          'pull': self.cli_args.build_pull,
                          'redhat': config.get('common', 'redhat'),
                          'target': self.cli_args.build_osbs_target,
                          'commit_msg': self.cli_args.build_osbs_commit_msg,
                          'base': self.generator.image.base
                          }

                builder = Builder(self.cli_commands[-1],
                                  self.cli_args.target,
                                  params)

                # Handle dependencies for selected builder, if any
                logger.debug("Checking CEKit build dependencies...")
                dependency_handler.handle(builder)

                builder.prepare(self.generator.image)
                builder.build()

            if 'test' in self.cli_commands:

                # XXX: fix this
                test_tags = []
                #test_tags = [self.generator.get_tags()[0]]
                # if wip is specified set tags to @wip
                if self.cli_args.wip:
                    test_tags = ['@wip']

                # at first we collect tests
                tc = TestCollector(os.path.dirname(self.cli_args.descriptor),
                                   self.cli_args.target)

                # we run the test only if we collect any
                # TODO investigate if we can improve handling different schema versions
                # self.generator.image.get('schema_version')
                if tc.collect('1', self.cli_args.steps_url):

                    # Handle test dependencies, if any
                    logger.debug("Checking CEKit test dependencies...")
                    dependency_handler.handle(tc)
                    runner = TestRunner(self.cli_args.target)
                    runner.run(self.cli_args.image, test_tags,
                               test_names=self.cli_args.names)
                else:
                    logger.warning("No test collected, test can't be run.")

            logger.info("Finished!")
            sys.exit(0)
        except KeyboardInterrupt as e:
            pass
        except CekitError as e:
            if self.cli_args.verbose:
                logger.exception(e)
            else:
                logger.error(e.message)
            sys.exit(1)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
