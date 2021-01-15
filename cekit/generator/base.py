# -*- coding: utf-8 -*-

import logging
import os
import platform
import re
import shutil

import yaml

from jinja2 import Environment, FileSystemLoader
from packaging.version import LegacyVersion, parse as parse_version

from cekit import tools
from cekit.config import Config
from cekit.descriptor import Env, Image, Label, Module, Overrides, Repository
from cekit.errors import CekitError
from cekit.template_helper import TemplateHelper
from cekit.version import version as cekit_version

LOGGER = logging.getLogger('cekit')
CONFIG = Config()


try:
    from odcs.client.odcs import ODCS, AuthMech
    # Requests is a dependency of ODCS client, so this should be safe
    import requests
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

    ODCS_HIDDEN_REPOS_FLAG = 'include_unpublished_pulp_repos'

    def __init__(self, descriptor_path, target, overrides):
        self._descriptor_path = descriptor_path
        self._overrides = []
        self.target = target
        self._fetch_repos = False
        self._module_registry = ModuleRegistry()
        self.image = None
        self.builder_images = []
        self.images = []

        if overrides:
            for override in overrides:
                # TODO: If the overrides is provided as text, why do we try to get path to it?
                LOGGER.debug("Loading override '{}'".format(override))
                self._overrides.append(Overrides(tools.load_descriptor(
                    override), os.path.dirname(os.path.abspath(override))))

        LOGGER.info("Initializing image descriptor...")

    @staticmethod
    def dependencies(params=None):
        deps = {}

        deps['odcs-client'] = {
            'package': 'python3-odcs-client',
            'library': 'odcs',
            'rhel': {
                'package': 'python2-odcs-client'
            }
        }

        if CONFIG.get('common', 'redhat'):
            deps['brew'] = {
                'package': 'brewkoji',
                'executable': '/usr/bin/brew'
            }

        return deps

    def init(self):
        """
        Initializes the image object.
        """

        LOGGER.debug("Removing old target directory")
        shutil.rmtree(self.target, ignore_errors=True)
        os.makedirs(os.path.join(self.target, 'image'))

        # Read the main image descriptor and create an Image object from it
        descriptor = tools.load_descriptor(self._descriptor_path)

        if isinstance(descriptor, list):
            LOGGER.info("Descriptor contains multiple elements, assuming multi-stage image")
            LOGGER.info("Found {} builder image(s) and one target image".format(
                len(descriptor[:-1])))

            # Iterate over images defined in image descriptor and
            # create Image objects out of them
            for image_descriptor in descriptor[:-1]:
                self.builder_images.append(
                    Image(image_descriptor, os.path.dirname(os.path.abspath(self._descriptor_path))))

            descriptor = descriptor[-1]

        self.image = Image(descriptor, os.path.dirname(os.path.abspath(self._descriptor_path)))

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

    def generate(self, builder):  # pylint: disable=unused-argument
        self.copy_modules()
        self.prepare_artifacts()
        self.prepare_repositories()
        self.image.remove_none_keys()
        self.image.write(os.path.join(self.target, 'image.yaml'))
        self.render_dockerfile()
        self.render_help()

    def add_redhat_overrides(self):
        self._overrides.append(self.get_redhat_overrides())

    def add_build_labels(self):
        image_labels = self.image.labels
        # we will persist cekit version in a label here, so we know which version of cekit
        # was used to build the image
        image_labels.append(Label({'name': 'io.cekit.version', 'value': cekit_version}))

        for label in image_labels:
            if len(label.value) > 128:
                # breaks the line each time it reaches 128 characters
                label.value = "\\\n".join(re.findall("(?s).{,128}", label.value))[:]

        # If we define the label in the image descriptor
        # we should *not* override it with value from
        # the root's key
        if self.image.description and not self.image.label('description'):
            image_labels.append(Label({'name': 'description', 'value': self.image.description}))

        # Last - if there is no 'summary' label added to image descriptor
        # we should use the value of the 'description' key and create
        # a 'summary' label with it's content. If there is even that
        # key missing - we should not add anything.
        description = self.image.label('description')

        if not self.image.label('summary') and description:
            image_labels.append(Label({'name': 'summary', 'value': description['value']}))

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
                    LOGGER.warning((
                        "Module repository '{0}' already added, please check your image configuration, " +
                        "skipping module repository '{0}'").format(repo.name))
                    continue
                # If the repository already exists, skip it
                repositories.append(repo)

        return repositories

    def build_module_registry(self):
        base_dir = os.path.join(self.target, 'repo')
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        for repo in self._module_repositories():
            LOGGER.debug("Downloading module repository: '{}'".format(repo.name))
            repo.copy(base_dir)
            self.load_repository(os.path.join(base_dir, repo.target))

    def load_repository(self, repo_dir):
        for modules_dir, _, files in os.walk(repo_dir):
            if 'module.yaml' in files:

                module_descriptor_path = os.path.abspath(os.path.expanduser(
                    os.path.normcase(os.path.join(modules_dir, 'module.yaml'))))

                module = Module(tools.load_descriptor(module_descriptor_path),
                                modules_dir,
                                os.path.dirname(module_descriptor_path))
                LOGGER.debug("Adding module '{}', path: '{}'".format(module.name, module.path))
                self._module_registry.add_module(module)

    def get_tags(self):
        return ["%s:%s" % (self.image['name'], self.image[
            'version']), "%s:latest" % self.image['name']]

    def copy_modules(self):
        """Prepare module to be used for Dockerfile generation.
        This means:

        1. Place module to args.target/image/modules/ directory

        """

        modules_to_install = []

        for module in self._modules():
            if module.install:
                modules_to_install += module.install

        target = os.path.join(self.target, 'image', 'modules')

        for module in modules_to_install:
            module = self._module_registry.get_module(
                module.name, module.version, suppress_warnings=True)
            LOGGER.debug("Copying module '{}' required by '{}'.".format(
                module.name, self.image.name))

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
                    Env({'name': 'JBOSS_IMAGE_NAME',
                         'value': '%s' % self._generator.image['name']}),
                    Env({'name': 'JBOSS_IMAGE_VERSION',
                         'value': '%s' % self._generator.image['version']})
                ]

            @property
            def labels(self):
                labels = [
                    Label({'name': 'name', 'value': '%s' % self._generator.image['name']}),
                    Label({'name': 'version', 'value': '%s' % self._generator.image['version']})
                ]
                return labels

        return RedHatOverrides(self)

    def render_dockerfile(self):
        """Renders Dockerfile to $target/image/Dockerfile"""
        LOGGER.info("Rendering Dockerfile...")

        template_file = os.path.join(os.path.dirname(__file__),
                                     '..',
                                     'templates',
                                     'template.jinja')
        loader = FileSystemLoader(os.path.dirname(template_file))
        env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
        env.globals['helper'] = TemplateHelper(self._module_registry)
        env.globals['image'] = self.image
        env.globals['builders'] = self.builder_images

        template = env.get_template(os.path.basename(template_file))

        dockerfile = os.path.join(self.target,
                                  'image',
                                  'Dockerfile')
        if not os.path.exists(os.path.dirname(dockerfile)):
            os.makedirs(os.path.dirname(dockerfile))

        with open(dockerfile, 'wb') as f:
            f.write(template.render(
                self.image).encode('utf-8'))
        LOGGER.debug("Dockerfile rendered")

    def render_help(self):
        """
        If requested, renders image help page based on the image descriptor.
        It is generated to the $target/image/help.md file and added later
        to the root of the image (/).
        """

        if not self.image.get('help', {}).get('add', False):
            return

        LOGGER.info("Rendering help.md page...")

        # Set default help template
        help_template_path = os.path.join(os.path.dirname(__file__),
                                          '..',
                                          'templates',
                                          'help.jinja')

        # If custom template is requested, use it
        if self.image.get('help', {}).get('template', ""):
            help_template_path = self.image['help']['template']

            # If the path provided is absolute, use it
            # If it's a relative path, make it relative to the image descriptor
            if not os.path.isabs(help_template_path):
                help_template_path = os.path.join(os.path.dirname(
                    self._descriptor_path), help_template_path)

        help_dirname, help_basename = os.path.split(help_template_path)

        loader = FileSystemLoader(help_dirname)
        env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
        env.globals['helper'] = TemplateHelper(self._module_registry)
        env.globals['image'] = self.image
        help_template = env.get_template(help_basename)

        helpfile = os.path.join(self.target, 'image', 'help.md')

        with open(helpfile, 'wb') as f:
            f.write(help_template.render(self.image).encode('utf-8'))

        LOGGER.debug("help.md rendered")

    def prepare_repositories(self):
        """ Prepare repositories for build time injection. """
        if 'packages' not in self.image:
            return

        if self.image.get('packages').get('content_sets'):
            LOGGER.warning(
                'The image has ContentSets repositories specified, all other repositories are removed!')
            self.image['packages']['repositories'] = []
        repos = self.image.get('packages').get('repositories', [])

        injected_repos = []

        for repo in repos:
            if self._handle_repository(repo):
                injected_repos.append(repo)

        if self.image.get('packages').get('content_sets'):
            url = self._prepare_content_sets(self.image.get('packages').get('content_sets'))
            if url:
                repo = Repository({'name': 'content_sets_odcs',
                                   'url': {'repository': url}})
                injected_repos.append(repo)
                self._fetch_repos = True

        if self._fetch_repos:
            for repo in injected_repos:
                repo.fetch(os.path.join(self.target, 'image', 'repos'))
            self.image['packages']['repositories_injected'] = injected_repos
        else:
            self.image['packages']['set_url'] = injected_repos

    def _prepare_content_sets(self, content_sets):
        if not content_sets:
            return False

        arch = platform.machine()

        if arch not in content_sets:
            raise CekitError("There are no content_sets defined for platform '{}'!".format(arch))

        repos = ' '.join(content_sets[arch])

        odcs_service_type = "Fedora"
        odcs_url = "https://odcs.fedoraproject.org"

        if CONFIG.get('common', 'redhat'):
            odcs_service_type = "Red Hat"
            odcs_url = "https://odcs.engineering.redhat.com"

        LOGGER.info("Using {} ODCS service to create composes".format(odcs_service_type))

        flags = []

        compose = self.image.get('osbs', {}).get(
            'configuration', {}).get('container', {}).get('compose', {})

        if compose.get(Generator.ODCS_HIDDEN_REPOS_FLAG, False):
            flags.append(Generator.ODCS_HIDDEN_REPOS_FLAG)

        odcs = ODCS(odcs_url, auth_mech=AuthMech.Kerberos)

        LOGGER.debug(
            "Requesting ODCS pulp compose for '{}' repositories with '{}' flags...".format(repos, flags))

        try:
            compose = odcs.new_compose(repos, 'pulp', flags=flags)
        except requests.exceptions.HTTPError as ex:
            if ex.response.status_code == 401:
                LOGGER.error(("You are not authorized to use {} ODCS service. "
                              "Are you sure you have a valid Kerberos session?").format(odcs_service_type))
            raise CekitError("Could not create ODCS compose", ex)

        compose_id = compose.get('id', None)

        if not compose_id:
            raise CekitError(
                "Invalid response from ODCS service: no compose id found: {}".format(compose))

        LOGGER.debug("Waiting for compose {} to finish...".format(compose_id))

        compose = odcs.wait_for_compose(compose_id, timeout=600)
        state = compose.get('state', None)

        if not state:
            raise CekitError(
                "Invalid response from ODCS service: no state found: {}".format(compose))

        # State 2 is "done"
        if state != 2:
            raise CekitError("Cannot create ODCS compose: '{}'".format(compose))

        LOGGER.debug("Compose finished successfully")

        repofile = compose.get('result_repofile', None)

        if not repofile:
            raise CekitError(
                "Invalid response from ODCS service: no state_repofile key found: {}".format(compose))

        return repofile

    def _handle_repository(self, repo):
        """Process and prepares all v2 repositories.

        Args:
          repo a repository to process

        Returns True if repository file is prepared and should be injected"""

        LOGGER.debug(
            "Loading configuration for repository: '{}' from 'repositories'.".format(repo['name']))

        if 'id' in repo:
            LOGGER.warning("Repository '{}' is defined as plain. It must be available "
                           "inside the image as Cekit will not inject it.".format(repo['name']))
            return False

        if 'content_sets' in repo:
            self._fetch_repos = True
            return self._prepare_content_sets(repo)

        elif 'rpm' in repo:
            self._prepare_repository_rpm(repo)
            return False

        elif 'url' in repo:
            return True

        return False

    def _prepare_repository_rpm(self, repo):
        raise NotImplementedError("RPM repository injection was not implemented!")

    def prepare_artifacts(self):
        raise NotImplementedError("Artifacts handling is not implemented")


class ModuleRegistry(object):
    def __init__(self):
        self._modules = {}
        self._defaults = {}

    def get_module(self, name, version=None, suppress_warnings=False):
        """
        Returns the module available in registry based on the name and version requested.

        If no modules are found for the requested name, an error is thrown. If version
        requirement could not be satisfied, an error is thrown too.

        If there is a version mismatch, default version is returned. See 'add_module'
        for more information how default versions are defined.

        Args:
            name (str): module name
            version (float or str): module version

        Returns:
            Module object.

        Raises:
            CekitError: If a module is not found or version requirement is not satisfied
        """

        # Get all modules for specied nam
        modules = self._modules.get(name, {})

        # If there are no modules with the requested name, fail
        if not modules:
            raise CekitError("There are no modules with '{}' name available".format(name))

        # If there is no module version requested, get default one
        if version is None:
            default_version = self._defaults.get(name)

            if not default_version:
                raise CekitError(
                    "Internal error: default version for module '{}' could not be found, please report it".format(name))

            default_module = self.get_module(name, default_version)

            if not suppress_warnings and len(modules) > 1:
                LOGGER.warning("Module version not specified for '{}' module, using '{}' default version".format(
                    name, default_version))

            return default_module

        # Finally, get the module for specified version
        module = modules.get(version)

        # If there is no such module, fail
        if not module:
            raise CekitError("Module '{}' with version '{}' could not be found, available versions: {}".format(
                name, version, ", ".join(list(modules.keys()))))

        return module

    def add_module(self, module):
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
            raise CekitError((
                "Internal error: module '{}' does not have version specified, "
                "we cannot add it to registry, please report it").format(module.name))

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
            raise CekitError("Module '{}' with version '{}' already exists in module registry".format(
                module.name, version))

        default_version = parse_version(self._defaults.get(module.name))
        current_version = parse_version(version)

        if isinstance(current_version, LegacyVersion):
            LOGGER.warning(("Module's '{}' version '{}' does not follow PEP 440 versioning scheme "
                            "(https://www.python.org/dev/peps/pep-0440), "
                            "we suggest follow this versioning scheme in modules").format(module.name, version))

        # If current module version is never, we need to make it the new default
        if current_version > default_version:
            self._defaults[module.name] = version

        # Finally add the module to registry
        modules[version] = module
