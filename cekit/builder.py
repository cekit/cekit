import logging

from cekit.config import Config
from cekit.errors import CekitError
from cekit.tools import DependencyHandler

LOGGER = logging.getLogger('cekit')
CONFIG = Config()


class Command(object):
    TYPE_BUILDER = 'builder'
    TYPE_TESTER = 'tester'

    def __init__(self, command, command_type):
        self._command = command
        self._type = command_type

        # Initialize dependency handler
        self.dependency_handler = DependencyHandler()

        LOGGER.debug("Checking CEKit core dependencies...")
        self.dependency_handler.handle_core_dependencies()

    def execute(self):
        self.prepare()
        self.run()

    def prepare(self):
        pass

    def run(self):
        raise CekitError(
            "Command.run() method is not implemented for '{}' command and '{}' type. Please report it!".format(self._command, self._type))


class Builder(Command):
    """
    Class representing generic builder - if it's instantiated it returns proper builder
    """

    def __init__(self, build_engine, params):
        self.params = params
        self.build_engine = build_engine

        self.target = self.params.target
        self.generator = None

        super(Builder, self).__init__(self.build_engine, Command.TYPE_BUILDER)

    def execute(self):
        self.prepare()
        self.before_generate()

        if self.params.validate:
            LOGGER.info(
                "The --validate parameter was specified, generation will not be performed, exiting")
            return

        self.generate()

        if self.params.dry_run:
            LOGGER.info("The --dry-run parameter was specified, build will not be executed, exiting")
            return

        self.before_build()
        self.run()

    def prepare(self):
        if self.build_engine == 'docker' or self.build_engine == 'buildah' or self.build_engine == "podman":
            from cekit.generator.docker import DockerGenerator as generator_impl
            LOGGER.info('Generating files for {} engine'.format(self.build_engine))
        elif self.build_engine == 'osbs':
            from cekit.generator.osbs import OSBSGenerator as generator_impl
            LOGGER.info('Generating files for OSBS engine')
        else:
            raise CekitError("Unsupported generator type: '{}'".format(self.build_engine))

        self.generator = generator_impl(self.params.descriptor,
                                        self.params.target,
                                        self.params.overrides)

        if CONFIG.get('common', 'redhat'):
            # Add the redhat specific stuff after everything else
            self.generator.add_redhat_overrides()

    def before_generate(self):
        # Handle dependencies for selected generator, if any
        LOGGER.debug("Checking CEKit generate dependencies...")
        self.dependency_handler.handle(self.generator, self.params)

        self.generator.init()

    def generate(self):
        self.generator.generate(self.build_engine)

    def before_build(self):
        LOGGER.debug("Checking CEKit build dependencies...")
        self.dependency_handler.handle(self, self.params)
