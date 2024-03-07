import logging
from typing import TYPE_CHECKING, Optional

from cekit.cekit_types import PathType
from cekit.config import Config
from cekit.errors import CekitError
from cekit.tools import DependencyHandler, Map

if TYPE_CHECKING:
    from cekit.generator.base import Generator

LOGGER = logging.getLogger("cekit")
CONFIG = Config()


class Command(object):
    TYPE_BUILDER = "builder"
    TYPE_TESTER = "tester"

    def __init__(self, command: str, command_type: str) -> None:
        self._command: str = command
        self._type: str = command_type

        # Initialize dependency handler
        self.dependency_handler: DependencyHandler = DependencyHandler()

        LOGGER.debug("Checking CEKit core dependencies...")
        self.dependency_handler.handle_core_dependencies()

    def execute(self):
        self.prepare()
        self.run()

    def prepare(self):
        pass

    def run(self):
        raise CekitError(
            "Command.run() method is not implemented for '{}' command and '{}' type. Please report it!".format(
                self._command, self._type
            )
        )


class Builder(Command):
    """
    Class representing generic builder - if it's instantiated it returns proper builder
    """

    def __init__(self, build_engine: str, params: Map) -> None:
        self.params = params
        self.build_engine: str = build_engine

        self.target: PathType = self.params.target
        self.generator: Optional[Generator] = None

        super(Builder, self).__init__(self.build_engine, Command.TYPE_BUILDER)

    def execute(self) -> None:
        self.prepare()
        self.before_generate()

        if self.params.validate:
            LOGGER.info(
                "The --validate parameter was specified, generation will not be performed, exiting"
            )
            return

        self.generate()

        if self.params.dry_run:
            LOGGER.info(
                "The --dry-run parameter was specified, build will not be executed, exiting"
            )
            return

        self.before_build()
        self.run()

    def prepare(self) -> None:
        if self.build_engine == "buildah" or self.build_engine == "podman":
            from cekit.generator.docker import DockerGenerator as generator_impl

            container_file: str = "Containerfile"
        elif self.build_engine == "docker":
            from cekit.generator.docker import DockerGenerator as generator_impl

            container_file: str = "Dockerfile"
        elif self.build_engine == "osbs":
            from cekit.generator.osbs import OSBSGenerator as generator_impl

            container_file: str = "Dockerfile"
        else:
            raise CekitError(f"Unsupported generator type: '{self.build_engine}'")
        LOGGER.info(f"Generating files for {self.build_engine} engine")

        if self.params.container_file:
            container_file: str = self.params.container_file

        self.generator = generator_impl(
            self.params.descriptor,
            self.params.target,
            container_file,
            self.params.overrides,
        )

        if CONFIG.get("common", "redhat"):
            # Add the redhat specific stuff after everything else
            self.generator.add_redhat_overrides()

    def before_generate(self) -> None:
        self.generator.init()

        LOGGER.debug("Checking CEKit generate dependencies...")
        # Handle dependencies for selected generator, if any
        self.dependency_handler.handle(self.generator, self.params)

    def generate(self) -> None:
        self.generator.generate()

    def before_build(self) -> None:
        LOGGER.debug("Checking CEKit build dependencies...")
        self.dependency_handler.handle(self, self.params)
