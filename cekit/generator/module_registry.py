import logging
from typing import NoReturn, Dict

from packaging.version import parse as parse_version, LegacyVersion

from cekit.errors import CekitError
from cekit.descriptor import Module

LOGGER = logging.getLogger("cekit")


class ModuleRegistry(object):

    def __init__(self):
        self._modules: Dict[str, Dict[str, Module]] = {}
        self._defaults: Dict[str, str] = {}

    def get_module(self, name, version=None, suppress_warnings=False) -> Module:
        """
        Returns the module available in registry based on the name and version requested.

        If no modules are found for the requested name, an error is thrown. If version
        requirement could not be satisfied, an error is thrown too.

        If there is a version mismatch, default version is returned. See 'add_module'
        for more information how default versions are defined.

        Args:
            name (str): module name
            version (float or str): module version
            suppress_warnings: whether to suppress warnings

        Returns:
            Module object.

        Raises:
            CekitError: If a module is not found or version requirement is not satisfied
        """

        # Get all modules for specfied nam
        modules = self._modules.get(name, {})

        # If there are no modules with the requested name, fail
        if not modules:
            raise CekitError(
                "There are no modules with '{}' name available".format(name)
            )

        # If there is no module version requested, get default one
        if version is None:
            default_version = self._defaults.get(name)

            if not default_version:
                raise CekitError(
                    "Internal error: default version for module '{}' could not be found, please report it".format(
                        name
                    )
                )

            default_module = self.get_module(name, default_version)

            if not suppress_warnings and len(modules) > 1:
                LOGGER.warning(
                    "Module version not specified for '{}' module, using '{}' default version".format(
                        name, default_version
                    )
                )

            return default_module

        # Finally, get the module for specified version
        module = modules.get(version)

        # If there is no such module, fail
        if not module:
            raise CekitError(
                "Module '{}' with version '{}' could not be found, available versions: {}".format(
                    name, version, ", ".join(list(modules.keys()))
                )
            )

        return module

    def add_module(self, module: Module) -> NoReturn:
        """
        Adds provided module to registry.

        If module of the same name and version already exists in registry,
        an error is raised.

        Module registry tracks default version for a particular module name.
        For this purpose the current version is compared with what is currently defined as
        the default version. If this newer, then the default version is replaced by the
        module we currently add to registry. For version comparison the package module
        (https://packaging.pypa.io/en/latest/) is used.

        Args:
            module (Module): module object to be added to registry

        Raises:
            CekitError: when module version is not provided or when a module with the same
                name and version already exists in registry.
        """

        # If module version is not provided, fail because it is required
        if not module.version:
            raise CekitError(
                (
                    "Internal error: module '{}' does not have version specified, "
                    "we cannot add it to registry, please report it"
                ).format(module.name)
            )

        # Convert version to string, it can be float or int, or anything actually
        version = str(module.version)

        # Get all modules from registry with the name of the module we want to add
        # There can be multiple versions of the same module
        modules = self._modules.get(module.name)

        # If there are no modules for the specified name this means
        # that this is the first one, add it and set it as default
        if not modules:
            # Set it to be the default module version
            self._defaults[module.name] = version
            self._modules[module.name] = {version: module}
            return

        # If a (different) module of specified name and version already exists in the registry - fail
        if version in modules and modules[version] != module:
            raise CekitError(
                "Module '{}' with version '{}' already exists in module registry".format(
                    module.name, version
                )
            )

        default_version = parse_version(self._defaults.get(module.name))
        current_version = parse_version(version)

        if isinstance(current_version, LegacyVersion):
            LOGGER.warning(
                (
                    "Module's '{}' version '{}' does not follow PEP 440 versioning scheme "
                    "(https://www.python.org/dev/peps/pep-0440), "
                    "we suggest follow this versioning scheme in modules"
                ).format(module.name, version)
            )

        # If current module version is never, we need to make it the new default
        if current_version > default_version:
            self._defaults[module.name] = version

        # Finally add the module to registry
        modules[version] = module

    def merge(self, other: 'ModuleRegistry') -> 'ModuleRegistry':
        # for module_name in set(self._modules).intersection(other._modules):
        #     # TODO: Improve merging to allow merging different versions
        #     raise CekitError("During merge, module '{}' already exists in module registry".format(module_name))

        self._modules.update(other._modules)
        self._defaults.update(other._defaults)