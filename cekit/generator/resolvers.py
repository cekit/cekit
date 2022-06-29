"""Resolvers for image and module descriptors

These resolvers are responsible for creating final image and module definitions, including overrides, recursion, etc.

"""
import logging
import os
from dataclasses import dataclass
from typing import NoReturn, List

from cekit.descriptor import Image, Resource, Module
from cekit.generator.module_registry import ModuleRegistry
from cekit.tools import load_yaml, normalize_path

LOGGER = logging.getLogger("cekit")


@dataclass
class CollectedImage:
    image: Image
    module_registry: ModuleRegistry
    build_images: List[Image]


@dataclass
class CollectedModule:
    module_registry: ModuleRegistry
    build_images: List[Image]


@dataclass
class CollectorData:
    build_dir: str


class ImageResolver(object):

    def __init__(self, data: CollectorData):
        self._data: CollectorData = data

    def resolve(self, image: Image, overrides) -> CollectedImage:

        LOGGER.debug("Resolving image %s and its dependencies", image.name)

        # Apply overrides to image definition:
        # intermediate (builder) images and target image as well
        # It is required to build the module registry
        image.apply_image_overrides(overrides)
        image.process_defaults()

        collected_module = ModuleCollector(image, self._data).collect()

        return CollectedImage(
            image=image,
            build_images=collected_module.build_images,
            module_registry=collected_module.module_registry
        )


class ModuleCollector(object):

    def __init__(self, image: Image, data: CollectorData):
        self._image: Image = image
        self._data: CollectorData = data

        self._registry: ModuleRegistry = ModuleRegistry()
        self._module_resolver: ModuleResolver = ModuleResolver(data)

    def collect(self) -> CollectedModule:

        registry = ModuleRegistry()

        if len(self._image.modules.install) == 0:
            # No modules to install
            return CollectedModule(module_registry=registry, build_images=list())

        for repository in self._image.modules.repositories:
            self._load_module_repository(repository, registry)

        module_resolver = ModuleResolver(self._data)

        build_images: List[Image] = []
        for install in self._image.modules.install:
            LOGGER.debug("Registering module %s required by %s", install.name, self._image.name)
            module = registry.get_module(install.name, install.version)

            collected = module_resolver.resolve(module)

            build_images.extend(collected.build_images)
            registry.merge(collected.module_registry)

        return CollectedModule(module_registry=registry, build_images=build_images)

    @property
    def _repository_dir(self) -> str:
        base_dir = os.path.join(self._data.build_dir, "repo")
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        return base_dir

    def _load_module_repository(self, module: Resource, registry: ModuleRegistry) -> NoReturn:
        # Make local copy of module repository
        LOGGER.debug("Downloading module repository: '{}'".format(module.name))
        if not os.path.exists(os.path.join(self._repository_dir, module.name)):
            # Since a module repository may be referenced from multiple places, only copy if it doesn't already exist.
            # TODO: this will cause different modules with the same name to clash.
            module.copy(self._repository_dir)

        # Load all modules in the repository into the registry
        self._load_modules(registry)

    def _load_modules(self, registry: ModuleRegistry) -> NoReturn:
        for modules_dir, _, files in os.walk(self._repository_dir):
            if "module.yaml" in files:
                module_descriptor_path = normalize_path(os.path.join(modules_dir, "module.yaml"))

                module_data = load_yaml(module_descriptor_path)
                module = Module(module_data, modules_dir, os.path.dirname(module_descriptor_path))

                LOGGER.debug(
                    "Adding module '{}', path: '{}'".format(module.name, module.path)
                )
                registry.add_module(module)


class ModuleResolver(object):

    def __init__(self, data: CollectorData):
        self._data: CollectorData = data

    def resolve(self, module: Module) -> CollectedModule:

        # TODO: Fix module overrides
        # module.apply_module_overrides()

        module_registry = ModuleRegistry()

        sub_build_images: List[Image] = list()
        build_images: List[Image] = module.build_images()
        for image in build_images:

            collected = ImageResolver(self._data).resolve(image, None)
            sub_build_images.extend(collected.build_images)
            sub_build_images.append(collected.image)
            module_registry.merge(collected.module_registry)

        return CollectedModule(
            module_registry=module_registry,
            build_images=sub_build_images
        )



    # module: Module = self._registry.get_module(
    #     install.name, install.version, suppress_warnings=True
    # )
    # LOGGER.debug(
    #     "Copying module '{}' required by '{}'.".format(
    #         module.name, self.image.name))
    #
    # dest = os.path.join(self._target_dir, module.name)
    #
    # if not os.path.exists(dest):
    #     LOGGER.debug("Copying module '{}' to: '{}'".format(module.name, dest))
    #     shutil.copytree(module.path, dest)
    #     # write out the module with any overrides
    # module.write(os.path.join(dest, "module.yaml"))
