# -*- coding: utf-8 -*-

import logging
import os
import platform
import re
import shutil
import tempfile
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.parse import urlparse

import yaml

from jinja2 import Environment, FileSystemLoader
from packaging.version import InvalidVersion, Version, _BaseVersion
from packaging.version import parse as parse_version

from cekit.cekit_types import PathType
from cekit.config import Config
from cekit.descriptor import (
    Env,
    Image,
    Label,
    Module,
    Modules,
    Overrides,
    Repository,
    Resource,
)
from cekit.errors import CekitError
from cekit.generator import legacy_version
from cekit.generator.legacy_version import LegacyVersion
from cekit.template_helper import TemplateHelper
from cekit.tools import (
    DependencyDefinition,
    Map,
    download_file,
    load_descriptor,
    parse_env_timeout,
)
from cekit.version import __version__ as cekit_version

if TYPE_CHECKING:
    from cekit.descriptor.modules import Install

LOGGER = logging.getLogger("cekit")
CONFIG = Config()

try:
    # Requests is a dependency of ODCS client, so this should be safe
    import requests
    from odcs.client.odcs import ODCS, AuthMech
except ModuleNotFoundError:
    pass


class Generator(object):
    """
    This class process Image descriptor(self.image) and uses it to generate
    target directory by fetching all dependencies and artifacts

    Args:
      descriptor_path - path to an image descriptor
      target - path to target directory
      overrides - path to overrides file (can be None)
    """

    ODCS_HIDDEN_REPOS_FLAG = "include_unpublished_pulp_repos"

    def __init__(
        self,
        descriptor_path: PathType,
        target: PathType,
        container_file: str,
        overrides: List[str],
    ):
        self._descriptor_path: PathType = descriptor_path
        self._overrides: List[Overrides] = []
        self.target: PathType = target
        self._fetch_repos = False
        self._module_registry: ModuleRegistry = ModuleRegistry()
        self.image: Optional[Image] = None
        self.builder_images: List[Image] = []
        self.images: List[Image] = []
        self.container_file: str = container_file

        # If descriptor has been passed in from standard input its not a path so use current working directory
        if "-" == descriptor_path:
            descriptor_path = os.getcwd()

        if overrides:
            for override in overrides:
                LOGGER.debug(f"Loading override '{override}'")
                if urlparse(override).scheme in ["http", "https", "file"]:
                    # HTTP Handling
                    tmpfile = tempfile.NamedTemporaryFile()
                    download_file(override, tmpfile.name)
                    self._overrides.append(
                        Overrides(
                            load_descriptor(tmpfile.name), os.path.dirname(tmpfile.name)
                        )
                    )
                else:
                    # File handling
                    override_artifact_dir = os.path.dirname(os.path.abspath(override))
                    if not os.path.exists(override):
                        override_artifact_dir = os.path.dirname(
                            os.path.abspath(descriptor_path)
                        )
                    self._overrides.append(
                        Overrides(load_descriptor(override), override_artifact_dir)
                    )

        LOGGER.info("Initializing image descriptor...")

    @staticmethod
    def dependencies(params: Map = None, image: Image = None) -> DependencyDefinition:
        deps = {}

        # Only activate dependency requirement for odcs if we have content_sets
        if image and image.get("packages").get("content_sets"):
            deps["odcs-client"] = {
                "package": "python3-odcs-client",
                "library": "odcs",
            }

        if CONFIG.get("common", "redhat"):
            deps["brew"] = {"package": "brewkoji", "executable": "brew"}
            # FOLLOW_TAG requires both version and release labels ; these are generally
            # only added consistently within RH and Fedora repos so currently this annotation
            # is only supported under the RH flag.
            deps["skopeo"] = {"package": "skopeo", "executable": "skopeo"}

        return deps

    def init(self):
        """
        Initializes the image object.
        """

        LOGGER.debug("Removing old target directory")
        shutil.rmtree(self.target, ignore_errors=True)
        os.makedirs(os.path.join(self.target, "image"))

        # Read the main image descriptor and create an Image object from it
        descriptor = load_descriptor(self._descriptor_path)

        if isinstance(descriptor, list):
            LOGGER.info(
                "Descriptor contains multiple elements, assuming multi-stage image"
            )
            LOGGER.info(
                f"Found {len(descriptor[:-1])} builder image(s) and one target image"
            )

            # Iterate over images defined in image descriptor and
            # create Image objects out of them
            for image_descriptor in descriptor[:-1]:
                self.builder_images.append(
                    Image(
                        image_descriptor,
                        os.path.dirname(os.path.abspath(self._descriptor_path)),
                    )
                )

            descriptor = descriptor[-1]

        self.image = Image(
            descriptor, os.path.dirname(os.path.abspath(self._descriptor_path))
        )

        # Construct list of all images (builder images + main one)
        self.images = [self.image] + self.builder_images

        for image in self.images:
            # Apply overrides to all image definitions:
            # intermediate (builder) images and target image as well
            # It is required to build the module registry
            image.apply_image_overrides(self._overrides)

        # Load definitions of modules
        # We need to load it after we apply overrides so that any changes to modules
        # will be reflected there as well
        self.build_module_registry()

        for image in self.images:
            # Process included modules
            image.apply_module_overrides(self._module_registry)
            image.process_defaults()

        # Add build labels
        self.add_build_labels()

    def generate(self):
        self.copy_modules()
        self.prepare_artifacts()
        self.prepare_repositories()
        self.image.remove_none_keys()
        self.image.write(os.path.join(self.target, "image.yaml"))
        self.render_image_file()
        self.render_help()

    def add_redhat_overrides(self):
        self._overrides.append(self.get_redhat_overrides())

    def add_build_labels(self):
        image_labels = self.image.labels
        # we will persist cekit version in a label here, so we know which version of cekit
        # was used to build the image
        image_labels.append(Label({"name": "io.cekit.version", "value": cekit_version}))

        for label in image_labels:
            if len(label.value) > 128:
                # breaks the line each time it reaches 128 characters
                label.value = "\\\n".join(re.findall("(?s).{,128}", label.value))[:]

        # If we define the label in the image descriptor
        # we should *not* override it with value from
        # the root's key
        if self.image.description and not self.image.label("description"):
            image_labels.append(
                Label({"name": "description", "value": self.image.description})
            )

        # Last - if there is no 'summary' label added to image descriptor
        # we should use the value of the 'description' key and create
        # a 'summary' label with it's content. If there is even that
        # key missing - we should not add anything.
        description = self.image.label("description")

        if not self.image.label("summary") and description:
            image_labels.append(
                Label({"name": "summary", "value": description["value"]})
            )

    def _modules(self) -> List["Modules"]:
        """
        Returns list of modules used in all builder images as well
        as the target image.
        """

        modules: List["Modules"] = []

        for image in self.images:
            if image.modules:
                modules += [image.modules]

        return modules

    def _module_repositories(self) -> List["Resource"]:
        """
        Prepares list of all module repositories. This includes repositories
        defined in builder images as well as target image.
        """
        repositories: List["Resource"] = []

        for module in self._modules():
            for repo in module.repositories:
                if repo in repositories:
                    LOGGER.warning(
                        (
                            "Module repository '{0}' already added, please check your image configuration, "
                            + "skipping module repository '{0}'"
                        ).format(repo.name)
                    )
                    continue
                # If the repository already exists, skip it
                repositories.append(repo)

        return repositories

    def build_module_registry(self) -> None:
        base_dir = os.path.join(self.target, "repo")
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        for repo in self._module_repositories():
            LOGGER.debug(f"Downloading module repository: '{repo.name}'")
            repo.copy(base_dir)
            self.load_repository(os.path.join(base_dir, repo.target))

    def load_repository(self, repo_dir: str) -> None:
        for modules_dir, _, files in os.walk(repo_dir):
            if "module.yaml" in files:
                module_descriptor_path = os.path.abspath(
                    os.path.expanduser(
                        os.path.normcase(os.path.join(modules_dir, "module.yaml"))
                    )
                )

                module = Module(
                    load_descriptor(module_descriptor_path),
                    modules_dir,
                    os.path.dirname(module_descriptor_path),
                )
                LOGGER.debug(f"Adding module '{module.name}', path: '{module.path}'")
                self._module_registry.add_module(module)

    def get_tags(self) -> List[str]:
        return [
            f"{self.image['name']}:{self.image['version']}",
            f"{self.image['name']}:latest",
        ]

    def copy_modules(self) -> None:
        """Prepare module to be used for Dockerfile generation.
        This means:

        1. Place module to args.target/image/modules/ directory

        """

        modules_to_install: List["Install"] = []

        for module in self._modules():
            if module.install:
                modules_to_install += module.install

        target = os.path.join(self.target, "image", "modules")

        for module in modules_to_install:
            module: "Module" = self._module_registry.get_module(
                module.name, module.version, suppress_warnings=True
            )
            LOGGER.debug(
                f"Copying module '{module.name}' required by '{self.image.name}'."
            )

            dest = os.path.join(target, module.name)

            if not os.path.exists(dest):
                LOGGER.debug(f"Copying module '{module.name}' to: '{dest}'")
                shutil.copytree(module.path, dest)
            # write out the module with any overrides
            module.write(os.path.join(dest, "module.yaml"))

    def get_redhat_overrides(self) -> Overrides:
        class RedHatOverrides(Overrides):
            def __init__(self, generator):
                super(RedHatOverrides, self).__init__({}, None)
                self._generator = generator

            @property
            def envs(self):
                return [
                    Env(
                        {
                            "name": "JBOSS_IMAGE_NAME",
                            "value": f"{self._generator.image['name']}",
                        }
                    ),
                    Env(
                        {
                            "name": "JBOSS_IMAGE_VERSION",
                            "value": f"{self._generator.image['version']}",
                        }
                    ),
                ]

            @property
            def labels(self):
                labels = [
                    Label(
                        {"name": "name", "value": f"{self._generator.image['name']}"}
                    ),
                    Label(
                        {
                            "name": "version",
                            "value": f"{self._generator.image['version']}",
                        }
                    ),
                ]
                return labels

        return RedHatOverrides(self)

    def render_image_file(self) -> None:
        """Renders Containerfile/Dockerfile to $target/image/Dockerfile or $target/image/Containerfile"""
        LOGGER.info(f"Rendering {self.container_file}...")

        template_file = os.path.join(
            os.path.dirname(__file__), "..", "templates", "template.jinja"
        )
        loader = FileSystemLoader(os.path.dirname(template_file))
        env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
        env.globals["helper"] = TemplateHelper(self._module_registry)
        env.globals["image"] = self.image
        env.globals["builders"] = self.builder_images

        template = env.get_template(os.path.basename(template_file))

        dockerfile = os.path.join(self.target, "image", self.container_file)
        if not os.path.exists(os.path.dirname(dockerfile)):
            os.makedirs(os.path.dirname(dockerfile))

        with open(dockerfile, "wb") as f:
            f.write(template.render(self.image).encode("utf-8"))
        LOGGER.debug(f"{self.container_file} rendered")

    def render_help(self) -> None:
        """
        If requested, renders image help page based on the image descriptor.
        It is generated to the $target/image/help.md file.
        """

        if not self.image.help.get("add", False):
            return

        # Set default help template
        help_template_path = os.path.join(
            os.path.dirname(__file__), "..", "templates", "help.jinja"
        )

        # If custom template is requested, use it
        if self.image.get("help", {}).get("template", ""):
            help_template_path = self.image["help"]["template"]

            # If the path provided is absolute, use it
            # If it's a relative path, make it relative to the image descriptor
            if not os.path.isabs(help_template_path):
                help_template_path = os.path.join(
                    os.path.dirname(self._descriptor_path), help_template_path
                )

        LOGGER.info(f"Rendering help.md page from template {help_template_path}")

        help_dirname, help_basename = os.path.split(help_template_path)
        loader = FileSystemLoader(help_dirname)
        env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
        env.globals["helper"] = TemplateHelper(self._module_registry)
        env.globals["image"] = self.image
        help_template = env.get_template(help_basename)
        help_file = os.path.join(self.target, "image", "help.md")

        with open(help_file, "wb") as f:
            f.write(help_template.render(self.image).encode("utf-8"))

        LOGGER.debug("help.md rendered")

    def prepare_repositories(self) -> None:
        """Prepare repositories for build time injection."""
        if "packages" not in self.image:
            return

        # TODO: Replace gets with the equivalent actual properties
        if self.image.get("packages").get("content_sets"):
            LOGGER.warning(
                "The image has ContentSets repositories specified, all other repositories are removed!"
            )
            self.image["packages"]["repositories"] = []
        repos: List[Repository] = self.image.get("packages").get("repositories", [])

        injected_repos: List[Repository] = []

        for repo in repos:
            if self._handle_repository(repo):
                injected_repos.append(repo)

        if self.image.get("packages").get("content_sets"):
            url = self._prepare_content_sets(
                self.image.get("packages").get("content_sets")
            )
            if url:
                repo = Repository(
                    {"name": "content_sets_odcs", "url": {"repository": url}}
                )
                injected_repos.append(repo)
                self._fetch_repos = True

        if self._fetch_repos:
            for repo in injected_repos:
                repo.fetch(os.path.join(self.target, "image", "repos"))
            self.image["packages"]["repositories_injected"] = injected_repos
        else:
            self.image["packages"]["set_url"] = injected_repos

    def _prepare_content_sets(self, content_sets: Repository):
        if not content_sets:
            return False

        from cekit.generator.behave import BehaveGenerator

        if isinstance(self, BehaveGenerator):
            LOGGER.warning("Running via Behave so not requesting ODCS compose")
            return False

        arch = platform.machine()

        if arch not in content_sets:
            raise CekitError(
                f"There are no content_sets defined for platform '{arch}'!"
            )

        repos = " ".join(content_sets[arch])

        odcs_service_type = "Fedora"
        odcs_url = "https://odcs.fedoraproject.org"

        if CONFIG.get("common", "redhat"):
            odcs_service_type = "Red Hat"
            odcs_url = "https://odcs.engineering.redhat.com"

        LOGGER.info(f"Using {odcs_service_type} ODCS service to create composes")

        flags = []

        compose = (
            self.image.get("osbs", {})
            .get("configuration", {})
            .get("container", {})
            .get("compose", {})
        )

        if compose.get(Generator.ODCS_HIDDEN_REPOS_FLAG, False):
            flags.append(Generator.ODCS_HIDDEN_REPOS_FLAG)

        odcs = ODCS(odcs_url, auth_mech=AuthMech.Kerberos)

        LOGGER.debug(
            "Requesting ODCS pulp compose for '{}' repositories with '{}' flags...".format(
                repos, flags
            )
        )

        try:
            compose = odcs.new_compose(repos, "pulp", flags=flags)
        except requests.exceptions.HTTPError as ex:
            if ex.response.status_code == 401:
                LOGGER.error(
                    (
                        "You are not authorized to use {} ODCS service. "
                        "Are you sure you have a valid Kerberos session?"
                    ).format(odcs_service_type)
                )
            raise CekitError("Could not create ODCS compose") from ex

        compose_id = compose.get("id", None)

        if not compose_id:
            raise CekitError(
                f"Invalid response from ODCS service: no compose id found: {compose}"
            )

        LOGGER.debug(f"Waiting for compose {compose_id} to finish...")

        compose = odcs.wait_for_compose(
            compose_id, timeout=parse_env_timeout("ODCS_TIMEOUT", "600")
        )
        state = compose.get("state", None)

        if not state:
            raise CekitError(
                f"Invalid response from ODCS service: no state found: {compose}"
            )

        # State 2 is "done"
        if state != 2:
            raise CekitError(f"Cannot create ODCS compose: '{compose}'")

        LOGGER.debug("Compose finished successfully")

        repofile = compose.get("result_repofile", None)

        if not repofile:
            raise CekitError(
                "Invalid response from ODCS service: no state_repofile key found: {}".format(
                    compose
                )
            )

        return repofile

    def _handle_repository(self, repo: Repository):
        """Process and prepares all v2 repositories.

        Args:
          repo a repository to process

        Returns True if repository file is prepared and should be injected"""

        LOGGER.debug(
            "Loading configuration for repository: '{}' from 'repositories'.".format(
                repo["name"]
            )
        )

        if "id" in repo:
            LOGGER.warning(
                "Repository '{}' is defined as plain. It must be available "
                "inside the image as Cekit will not inject it.".format(repo["name"])
            )
            return False

        elif "rpm" in repo:
            self._prepare_repository_rpm(repo)
            return False

        elif "url" in repo:
            return True

        return False

    def _prepare_repository_rpm(self, repo):
        pass

    def prepare_artifacts(self):
        raise NotImplementedError("Artifacts handling is not implemented")


class ModuleRegistry(object):
    def __init__(self):
        self._modules: Dict[str, Dict[str, Module]] = {}
        self._defaults: Dict[str, str] = {}

    def get_module(self, name, version: Any = None, suppress_warnings=False) -> Module:
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

        # Get all modules for specied nam
        modules = self._modules.get(name, {})

        # If there are no modules with the requested name, fail
        if not modules:
            raise CekitError(f"There are no modules with '{name}' name available")

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

    def add_module(self, module: Module):
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

        # If a module of specified name and version already exists in the registry - fail
        if version in modules:
            raise CekitError(
                "Module '{}' with version '{}' already exists in module registry".format(
                    module.name, version
                )
            )

        current_version: _BaseVersion = internal_parse_version(version, module.name)
        default_version: _BaseVersion = internal_parse_version(
            self._defaults.get(module.name), module.name
        )

        # If current module version is newer, we need to make it the new default
        if current_version > default_version:
            self._defaults[module.name] = version

        # Finally add the module to registry
        modules[version] = module


def internal_parse_version(version: str, module_name: str) -> _BaseVersion:
    try:
        result: Version = parse_version(version)
        # This if block is only for Python3.6 compatibility which still might return
        # a LegacyVersion and not throw an exception. LegacyVersion does not have
        # that field so can be used to differentiate.
        if not hasattr(result, "major"):
            raise InvalidVersion
    except InvalidVersion:
        LOGGER.error(
            f"Module's '{module_name}' version '{version}' does not follow PEP 440 versioning "
            "scheme (https://www.python.org/dev/peps/pep-0440) which should be followed in modules."
        )
        result: LegacyVersion = legacy_version.parse(version)
    return result
