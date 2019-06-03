# -*- coding: utf-8 -*-

import logging
import os
import re
import platform
import shutil

import yaml

from jinja2 import Environment, FileSystemLoader

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

        if overrides:
            for override in overrides:
                # TODO: If the overrides is provided as text, why do we try to get path to it?
                LOGGER.debug("Loading override '%s'" % (override))
                self._overrides.append(Overrides(tools.load_descriptor(
                    override), os.path.dirname(os.path.abspath(override))))

        LOGGER.info("Initializing image descriptor...")

    @staticmethod
    def dependencies():
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

        # Read the main image descriptor and create an Image object from it
        descriptor = tools.load_descriptor(self._descriptor_path)
        self.image = Image(descriptor, os.path.dirname(os.path.abspath(self._descriptor_path)))

        # apply overrides to the image definition
        self.image.apply_image_overrides(self._overrides)
        # add build labels
        self.add_build_labels()
        # load the definitions of the modules
        self.build_module_registry()
        # process included modules
        self.apply_module_overrides()
        self.image.process_defaults()

    def generate(self, builder):
        self.copy_modules()
        self.prepare_artifacts()
        self.prepare_repositories(builder)
        self.image.remove_none_keys()
        self.image.write(os.path.join(self.target, 'image.yaml'))
        self.render_dockerfile()
        self.render_help()

    def add_tech_preview_overrides(self):
        self._overrides.append(self.get_tech_preview_overrides())

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

    def apply_module_overrides(self):
        self.image.apply_module_overrides(self._module_registry)

    def build_module_registry(self):
        base_dir = os.path.join(self.target, 'repo')
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        for repo in self.image.modules.repositories:
            LOGGER.debug("Downloading module repository: '%s'" % (repo.name))
            repo.copy(base_dir)
            self.load_repository(os.path.join(base_dir, repo.target_file_name()))

    def load_repository(self, repo_dir):
        for modules_dir, _, files in os.walk(repo_dir):
            if 'module.yaml' in files:

                module_descriptor_path = os.path.abspath(os.path.expanduser(
                    os.path.normcase(os.path.join(modules_dir, 'module.yaml'))))

                module = Module(tools.load_descriptor(module_descriptor_path),
                                modules_dir,
                                os.path.dirname(module_descriptor_path))
                LOGGER.debug("Adding module '%s', path: '%s'" % (module.name, module.path))
                self._module_registry.add_module(module)

    def get_tags(self):
        return ["%s:%s" % (self.image['name'], self.image[
            'version']), "%s:latest" % self.image['name']]

    def copy_modules(self):
        """Prepare module to be used for Dockerfile generation.
        This means:

        1. Place module to args.target/image/modules/ directory

        """
        target = os.path.join(self.target, 'image', 'modules')
        for module in self.image.modules.install:
            module = self._module_registry.get_module(module.name, module.version)
            LOGGER.debug("Copying module '%s' required by '%s'."
                         % (module.name, self.image.name))

            dest = os.path.join(target, module.name)

            if not os.path.exists(dest):
                LOGGER.debug("Copying module '%s' to: '%s'" % (module.name, dest))
                shutil.copytree(module.path, dest)
            # write out the module with any overrides
            module.write(os.path.join(dest, "module.yaml"))

    def get_tech_preview_overrides(self):
        class TechPreviewOverrides(Overrides):
            def __init__(self, generator):
                super(TechPreviewOverrides, self).__init__({}, None)
                self._generator = generator

            @property
            def name(self):
                new_name = self._generator.image.name
                if '/' in new_name:
                    family, new_name = new_name.split('/')
                    new_name = "%s-tech-preview/%s" % (family, new_name)
                else:
                    new_name = "%s-tech-preview" % new_name
                return new_name

        return TechPreviewOverrides(self)

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
        help_template = env.get_template(help_basename)

        helpfile = os.path.join(self.target, 'image', 'help.md')

        with open(helpfile, 'wb') as f:
            f.write(help_template.render(self.image).encode('utf-8'))

        LOGGER.debug("help.md rendered")

    def prepare_repositories(self, builder):
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
                LOGGER.error("You are not authorized to use {} ODCS service. Are you sure you have a valid Kerberos session?".format(
                    odcs_service_type))
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
            LOGGER.warning("Repository '%s' is defined as plain. It must be available "
                           "inside the image as Cekit will not inject it."
                           % repo['name'])
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

    def get_module(self, name, version=None):
        versions = self._modules.get(name, {})
        if version == None:
            default = versions.get('default')
            if len(versions) > 2:  # we always add the first seen as 'default'
                LOGGER.warning("Module version not specified for %s, using %s version." %
                               (name, default.version))
            return default
        return versions.get(version, None)

    def add_module(self, module):
        versions = self._modules.get(module.name)
        if not versions:
            versions = {}
            self._modules[module.name] = versions
        version = module.version
        if not version:
            version = 'None'
        existing = versions.get(version, None)
        if existing:
            raise CekitError("Duplicate module (%s:%s) found while processing module repository"
                             % (module.name, module.version))
        if len(versions) == 0:
            # for better or worse...
            versions['default'] = module
        versions[version] = module
