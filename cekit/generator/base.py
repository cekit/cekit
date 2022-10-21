# -*- coding: utf-8 -*-

import logging
import os
import platform
import re
import shutil
import tempfile
from typing import List
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader

from cekit.config import Config
from cekit.descriptor import Env, Label, Module, Overrides, Repository
from cekit.errors import CekitError
from cekit.template_helper import TemplateHelper
from cekit.tools import download_file, load_yaml
from cekit.version import __version__ as cekit_version
from cekit.descriptor import Image
from cekit.generator.module_registry import ModuleRegistry
from cekit.generator.resolvers import ImageResolver, CollectorData, CollectedImage

LOGGER = logging.getLogger("cekit")
CONFIG = Config()

try:
    # Requests is a dependency of ODCS client, so this should be safe
    import requests
    from odcs.client.odcs import ODCS, AuthMech
except ImportError:
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

    def __init__(self, descriptor_path, target, overrides):
        self._descriptor_path = descriptor_path
        self._overrides = []
        self.target = target
        self._fetch_repos = False
        self._module_registry = ModuleRegistry()
        self.image = None
        self.builder_images: List[Image] = []
        self.images: List[Image] = []

        # If descriptor has been passed in from standard input its not a path so use current working directory
        if "-" == descriptor_path:
            descriptor_path = os.getcwd()

        if overrides:
            for override in overrides:

                LOGGER.debug("Loading override '{}'".format(override))
                if urlparse(override).scheme in ["http", "https", "file"]:
                    # HTTP Handling
                    tmpfile = tempfile.NamedTemporaryFile()
                    download_file(override, tmpfile.name)
                    self._overrides.append(
                        Overrides(
                            load_yaml(tmpfile.name), os.path.dirname(tmpfile.name)
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
                        Overrides(load_yaml(override), override_artifact_dir)
                    )

        LOGGER.info("Initializing image descriptor...")

    @staticmethod
    def dependencies(params=None):
        deps = {}

        deps["odcs-client"] = {
            "package": "python3-odcs-client",
            "library": "odcs",
        }

        if CONFIG.get("common", "redhat"):
            deps["brew"] = {"package": "brewkoji", "executable": "/usr/bin/brew"}
            # FOLLOW_TAG requires both version and release labels ; these are generally
            # only added consistently within RH and Fedora repos so currently this annotation
            # is only supported under the RH flag.
            deps["skopeo"] = {"package": "skopeo", "executable": "/usr/bin/skopeo"}

        return deps

    def init(self):
        """
        Initializes the image object.
        """

        self._clean_target_directory()

        collected = self._load_main_image_descriptor()

        self.image = collected.image
        self.builder_images = collected.build_images
        self._module_registry = collected.module_registry

        # Construct list of all images (builder images + main one)
        self.images = [self.image] + self.builder_images

        for image in self.images:
            # Process included modules
            image.apply_module_overrides(self._module_registry)
            # image.process_defaults()

        # Add build labels
        self.add_build_labels()

    def _load_main_image_descriptor(self):

        image_resolver = ImageResolver(CollectorData(self.target))

        registry = ModuleRegistry()
        build_images = list()
        # Read the main image descriptor and create an Image object from it, while also collecting any build images
        # defined in the image descriptor (i.e. multi-stage build).
        descriptor = load_yaml(self._descriptor_path)
        if isinstance(descriptor, list):
            LOGGER.info(
                "Descriptor contains multiple elements, assuming multi-stage image"
            )
            LOGGER.info(
                "Found {} builder image(s) and one target image".format(
                    len(descriptor[:-1])
                )
            )

            # Iterate over images defined in image descriptor and
            # create Image objects out of them
            for image_descriptor in descriptor[:-1]:
                build_image = Image(
                    image_descriptor,
                    os.path.dirname(os.path.abspath(self._descriptor_path)),
                )

                collected = image_resolver.resolve(build_image, self._overrides)
                registry.merge(collected.module_registry)
                build_images.append(build_image)
                build_images.extend(collected.build_images)

            descriptor = descriptor[-1]
        image = Image(
            descriptor, os.path.dirname(os.path.abspath(self._descriptor_path))
        )
        collected = image_resolver.resolve(image, self._overrides)
        registry.merge(collected.module_registry)
        build_images.extend(collected.build_images)

        return CollectedImage(image, registry, build_images)


    def _clean_target_directory(self):
        LOGGER.debug("Removing old target directory")
        shutil.rmtree(self.target, ignore_errors=True)
        os.makedirs(os.path.join(self.target, "image"))

    def generate(self):
        self.copy_modules(self._modules())
        self.prepare_artifacts()
        self.prepare_repositories()
        self.image.remove_none_keys()
        self.image.write(os.path.join(self.target, "image.yaml"))
        self.render_dockerfile()
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

    def _modules(self):
        """
        Returns list of modules used in all builder images as well
        as the target image.
        """

        modules = []

        for image in self.images:
            if image.modules:
                modules += [image.modules]

        return modules

    def _module_repositories(self):
        """
        Prepares list of all module repositories. This includes repositories
        defined in builder images as well as target image.
        """
        repositories = []

        for module in self._modules():
            for repo in module.repositories:
                if repo in repositories:
                    # If the repository already exists, skip it
                    LOGGER.warning(
                        (
                                "Module repository '{0}' already added, please check your image configuration, "
                                + "skipping module repository '{0}'"
                        ).format(repo.name)
                    )
                    continue
                repositories.append(repo)

        return repositories

    def get_tags(self):
        return [
            "%s:%s" % (self.image["name"], self.image["version"]),
            "%s:latest" % self.image["name"],
        ]

    def copy_modules(self, modules):
        """Prepare module to be used for Dockerfile generation.
        This means:

        1. Place module to args.target/image/modules/ directory

        """

        modules_to_install = []

        for image_module_list in modules:
            for module_key in image_module_list.install:
                module: Module = self._module_registry.get_module(
                    module_key.name, module_key.version, suppress_warnings=True
                )
                modules_to_install.append(module)

        target = os.path.join(self.target, "image", "modules")

        for module in modules_to_install:
            LOGGER.debug(
                "Copying module '{}' required by '{}'.".format(
                    module.name, self.image.name
                )
            )

            dest = os.path.join(target, module.name)

            if not os.path.exists(dest):
                LOGGER.debug("Copying module '{}' to: '{}'".format(module.name, dest))
                shutil.copytree(module.path, dest)
            # write out the module with any overrides
            module.write(os.path.join(dest, "module.yaml"))

    def get_redhat_overrides(self):
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
                            "value": "%s" % self._generator.image["name"],
                        }
                    ),
                    Env(
                        {
                            "name": "JBOSS_IMAGE_VERSION",
                            "value": "%s" % self._generator.image["version"],
                        }
                    ),
                ]

            @property
            def labels(self):
                labels = [
                    Label(
                        {"name": "name", "value": "%s" % self._generator.image["name"]}
                    ),
                    Label(
                        {
                            "name": "version",
                            "value": "%s" % self._generator.image["version"],
                        }
                    ),
                ]
                return labels

        return RedHatOverrides(self)

    def render_dockerfile(self):
        """Renders Dockerfile to $target/image/Dockerfile"""
        LOGGER.info("Rendering Dockerfile...")

        template_file = os.path.join(
            os.path.dirname(__file__), "..", "templates", "template.jinja"
        )
        loader = FileSystemLoader(os.path.dirname(template_file))
        env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
        env.globals["helper"] = TemplateHelper(self._module_registry)
        env.globals["image"] = self.image
        env.globals["builders"] = self.builder_images

        template = env.get_template(os.path.basename(template_file))

        dockerfile = os.path.join(self.target, "image", "Dockerfile")
        if not os.path.exists(os.path.dirname(dockerfile)):
            os.makedirs(os.path.dirname(dockerfile))

        with open(dockerfile, "wb") as f:
            f.write(template.render(self.image).encode("utf-8"))
        LOGGER.debug("Dockerfile rendered")

    def render_help(self):
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

        LOGGER.info(
            "Rendering help.md page from template {}".format(help_template_path)
        )

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

    def prepare_repositories(self):
        """Prepare repositories for build time injection."""
        if "packages" not in self.image:
            return

        if self.image.get("packages").get("content_sets"):
            LOGGER.warning(
                "The image has ContentSets repositories specified, all other repositories are removed!"
            )
            self.image["packages"]["repositories"] = []
        repos = self.image.get("packages").get("repositories", [])

        injected_repos = []

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

    def _prepare_content_sets(self, content_sets):
        if not content_sets:
            return False

        arch = platform.machine()

        if arch not in content_sets:
            raise CekitError(
                "There are no content_sets defined for platform '{}'!".format(arch)
            )

        repos = " ".join(content_sets[arch])

        odcs_service_type = "Fedora"
        odcs_url = "https://odcs.fedoraproject.org"

        if CONFIG.get("common", "redhat"):
            odcs_service_type = "Red Hat"
            odcs_url = "https://odcs.engineering.redhat.com"

        LOGGER.info(
            "Using {} ODCS service to create composes".format(odcs_service_type)
        )

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
            raise CekitError("Could not create ODCS compose", ex)

        compose_id = compose.get("id", None)

        if not compose_id:
            raise CekitError(
                "Invalid response from ODCS service: no compose id found: {}".format(
                    compose
                )
            )

        LOGGER.debug("Waiting for compose {} to finish...".format(compose_id))

        compose = odcs.wait_for_compose(compose_id, timeout=600)
        state = compose.get("state", None)

        if not state:
            raise CekitError(
                "Invalid response from ODCS service: no state found: {}".format(compose)
            )

        # State 2 is "done"
        if state != 2:
            raise CekitError("Cannot create ODCS compose: '{}'".format(compose))

        LOGGER.debug("Compose finished successfully")

        repofile = compose.get("result_repofile", None)

        if not repofile:
            raise CekitError(
                "Invalid response from ODCS service: no state_repofile key found: {}".format(
                    compose
                )
            )

        return repofile

    def _handle_repository(self, repo):
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

        if "content_sets" in repo:
            self._fetch_repos = True
            return self._prepare_content_sets(repo)

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


