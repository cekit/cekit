import copy
from collections import OrderedDict

import yaml

import cekit
from cekit.descriptor import Descriptor, Label, Env, Port, Run, Modules, Packages, Osbs, Volume
from cekit.descriptor.resource import create_resource
from cekit.descriptor.base import logger, _merge_descriptors
from cekit.errors import CekitError

_image_schema = yaml.safe_load("""
map:
  name: {type: str, required: True}
  version: {type: text, required: True}
  schema_version: {type: int}
  release: {type: text}
  from: {type: str}
  description: {type: text}
  labels: {type: any}
  envs:  {type: any}
  execute: {type: any}
  ports: {type: any}
  run: {type: any}
  artifacts: {type: any}
  modules: {type: any}
  packages: {type: any}
  osbs: {type: any}
  volumes: {type: any}
  help:
    map:
      add: {type: bool}
      template: {type: text}""")


def get_image_schema():
    return copy.deepcopy(_image_schema)


class Image(Descriptor):
    def __init__(self, descriptor, artifact_dir):
        self._artifact_dir = artifact_dir
        self.path = artifact_dir
        self.schema = _image_schema.copy()
        super(Image, self).__init__(descriptor)
        self.skip_merging = ['description',
                             'version',
                             'name',
                             'release']
        self._prepare()

    def _prepare(self):
        self._descriptor['labels'] = [Label(x) for x in self._descriptor.get('labels', [])]
        self._descriptor['envs'] = [Env(x) for x in self._descriptor.get('envs', [])]
        self._descriptor['ports'] = [Port(x) for x in self._descriptor.get('ports', [])]
        if 'run' in self._descriptor:
            self._descriptor['run'] = Run(self._descriptor['run'])
        self._descriptor['artifacts'] = [create_resource(a, directory=self._artifact_dir)
                                         for a in self._descriptor.get('artifacts', [])]
        self._descriptor['modules'] = Modules(self._descriptor.get('modules', {}), self.path)
        self._descriptor['packages'] = Packages(self._descriptor.get('packages', {}), self.path)
        self._descriptor['osbs'] = Osbs(self._descriptor.get('osbs', {}), self.path)
        self._descriptor['volumes'] = [Volume(x) for x in self._descriptor.get('volumes', [])]

        # make sure image declarations override any module definitions
        self._image_overrides = {'artifacts': Image._to_dict(
            self.artifacts), 'modules': Image._to_dict(self.modules.install)}
        self._all_artifacts = Image._to_dict(self.artifacts)

    def process_defaults(self):
        """Prepares default values before rendering"""
        if not self.run:
            self.run = Run({})

        # do we want to force a user?
        if 'user' not in self.run:
            self.run._descriptor['user'] = cekit.DEFAULT_USER

        # Default package manager is yum
        if not self.packages.manager:
            self.packages._descriptor['manager'] = 'yum'

        # Default directory for supplementary files that should be copied to dist-git directory
        if not self.osbs.extra_dir:
            self.osbs._descriptor['extra_dir'] = 'osbs_extra'

    @property
    def name(self):
        return self.get('name')

    @name.setter
    def name(self, value):
        self._descriptor['name'] = value

    @property
    def version(self):
        return self.get('version')

    @version.setter
    def version(self, value):
        self._descriptor['version'] = value

    @property
    def release(self):
        return self.get('release')

    @release.setter
    def release(self, value):
        self._descriptor['release'] = value

    @property
    def base(self):
        return self.get('from')

    @base.setter
    def base(self, value):
        self._descriptor['from'] = value

    @property
    def description(self):
        return self.get('description')

    @description.setter
    def description(self, value):
        self._descriptor['description'] = value

    @property
    def labels(self):
        return self.get('labels', [])

    @property
    def envs(self):
        return self.get('envs', [])

    @property
    def ports(self):
        return self.get('ports', [])

    @property
    def run(self):
        return self.get('run')

    @run.setter
    def run(self, value):
        self._descriptor['run'] = value

    @property
    def all_artifacts(self):
        return self._all_artifacts.values()

    @property
    def artifacts(self):
        return self.get('artifacts', [])

    @property
    def modules(self):
        return self.get('modules', Modules({}, self._artifact_dir))

    @property
    def packages(self):
        return self.get('packages', Packages({}, self.path))

    @property
    def osbs(self):
        return self.get('osbs')

    @osbs.setter
    def osbs(self, value):
        self._descriptor['osbs'] = value

    @property
    def volumes(self):
        return self.get('volumes', [])

    @property
    def help(self):
        return self.get('help', {})

    def apply_image_overrides(self, overrides):
        """
        Applies overrides to the image descriptor.
        """
        if not overrides:
            return
        for override in overrides:
            if override.name:
                self.name = override.name
            if override.version:
                self.version = override.version
            if override.base:
                self.base = override.base
            if override.description:
                self.description = override.description

            labels = Image._to_dict(self.labels)
            for label in override.labels:
                name = label.name
                if name in labels:
                    labels[name] = label.merge(labels[name])
                else:
                    labels[name] = label
            self._descriptor['labels'] = list(labels.values())

            envs = Image._to_dict(self.envs)
            for env in override.envs:
                name = env.name
                if name in envs:
                    envs[name] = env.merge(envs[name])
                else:
                    envs[name] = env
            self._descriptor['envs'] = list(envs.values())

            ports = Image._to_dict(self.ports)
            for port in override.ports:
                name = port.value
                if name in ports:
                    ports[name] = port.merge(ports[name])
                else:
                    ports[name] = port
            self._descriptor['ports'] = list(ports.values())

            module_repositories = Image._to_dict(self.modules.repositories)
            for repository in override.modules.repositories:
                name = repository.name
                if name in module_repositories:
                    module_repositories[name] = repository.merge(module_repositories[name])
                else:
                    module_repositories[name] = repository
            self.modules._descriptor['repositories'] = list(module_repositories.values())

            self.packages._descriptor = override.packages.merge(self.packages)

            # In case content sets are provided as null values
            # Remove the key entirely.
            # TODO: This should be handled probably at general level, for every key
            for flag in ['content_sets', 'content_sets_file']:
                if flag in override.packages and override.packages[flag] is None:
                    self.packages._descriptor.pop('content_sets', None)
                    self.packages._descriptor.pop('content_sets_file', None)

            if override.osbs is not None:
                self.osbs = override.osbs.merge(self.osbs)

            for package in override.packages.install:
                if package not in self.packages.install:
                    self.packages.install.append(package)

            artifact_overrides = self._image_overrides['artifacts']
            image_artifacts = Image._to_dict(self.artifacts)
            for artifact in override.artifacts:
                name = artifact.name
                # collect override so we can apply it to modules
                artifact_overrides[name] = artifact
                # add it to the list of everything
                self._all_artifacts[name] = artifact
                # Apply override to image descriptor
                image_artifacts[name] = artifact
            self._descriptor['artifacts'] = list(image_artifacts.values())

            module_overrides = self._image_overrides['modules']
            image_modules = Image._to_dict(self.modules.install)
            for module in override.modules.install:
                name = module.name
                # collect override so we can apply it to modules.
                # this allows us to override module versions without affecting ordering.
                module_overrides[name] = module
                # Apply override to image descriptor
                # If the module does not exists in the original descriptor, add it there
                image_modules[name] = module
            self.modules._descriptor['install'] = list(image_modules.values())

            if override.run != None:
                if self.run:
                    self.run = override.run.merge(self.run)
                else:
                    self.run = override.run

    def apply_module_overrides(self, module_registry):
        """
        Applies overrides to included modules.  This includes:
            Artifact definitions
            Module dependency version overrides
        Also incorporates module contributed global configuration into the image:
            Run specification
            Package repository definitions
            Required artifacts
        """
        install_list = OrderedDict()

        # index by name for easier access
        self._package_repositories = Image._to_dict(self.packages.repositories)

        # collect final 'run' value from modules
        self._module_run = Run({})

        # process the modules and integrate relevant bits into ourself
        self.process_install_list(self, self.modules.install, install_list, module_registry)

        # update ourself based on module declarations
        # final order of modules to be installed
        self.modules._descriptor['install'] = list(install_list.values())
        # all package repositories required for installing packages
        self.packages._descriptor['repositories'] = list(self._package_repositories.values())
        # final 'run' value
        if self.run:
            self.run = self.run.merge(self._module_run)
        else:
            self.run = self._module_run

    def process_install_list(self, source, to_install_list, install_list, module_registry):
        module_overrides = self._image_overrides['modules']
        artifact_overrides = self._image_overrides['artifacts']
        for to_install in to_install_list:
            logger.debug("Preparing module '{}' required by '{}'.".format(
                to_install.name, source.name))
            override = module_overrides.get(to_install.name, None)
            if override:
                if override.version != to_install.version:
                    logger.debug("Module '{}:{}' being overridden with '{}:{}'.".format
                                 (to_install.name, to_install.version, override.name, override.version))
                # apply module override
                to_install = override

            existing = install_list.get(to_install.name, None)
            # see if we've already processed this
            if existing:
                # check for a version conflict
                if existing.version != to_install.version:
                    logger.warning("Module version inconsistency for {}: {} requested, but {} will be used.".format(
                        to_install.name, to_install.version, existing.version))
                continue

            module = module_registry.get_module(to_install.name, to_install.version)
            if not module:
                raise CekitError("Could not locate module %s version %s. Please verify that it is included in one of the "
                                 "specified module repositories." % (to_install.name, to_install.version))

            # collect artifacts and apply overrides
            module_artifacts = Image._to_dict(module.artifacts)
            for artifact in module.artifacts:
                name = artifact.name
                if name in artifact_overrides:
                    override = artifact_overrides[name]
                    self._all_artifacts[name] = override
                    module_artifacts[name] = override
                else:
                    self._all_artifacts[name] = artifact
            module._descriptor['artifacts'] = list(module_artifacts.values())

            # collect package repositories
            for repo in module.packages.repositories:
                name = repo.name
                if not name in self._package_repositories:
                    self._package_repositories[name] = repo

            # incorporate run specification contributed by module
            if module.run:
                # we're looping in order of install, so we want the current module to override whatever we have
                self._module_run = module.run.merge(self._module_run)

            # prevent circular dependencies. we'll move it to the end after processing
            install_list[to_install.name] = to_install

            # process this modules dependencies
            self.process_install_list(module, module.modules.install, install_list, module_registry)

            # move this module to the end of the list.
            install_list.pop(to_install.name)
            install_list[to_install.name] = to_install

    # helper to simplify merging lists of objects
    @classmethod
    def _to_dict(cls, named_items, key='name'):
        dictionary = OrderedDict()
        for item in named_items:
            dictionary[item[key]] = item
        return dictionary
