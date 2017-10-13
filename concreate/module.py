import os
import logging

from concreate.descriptor import Descriptor
from concreate.errors import ConcreateError
from concreate.resource import Resource

logger = logging.getLogger('concreate')
# importable list of all modules
modules = []


def copy_module_to_target(name, version, target):
    """Copies a module from args.target/repo/... directory into
    args.target/image/modules/... and update module path to be
    the new location

    Arguments:
    name - name of the module to lookup in modules list
    version - version of the module to used
    target - directory where module will be copied

    Returns instance of copied module.
    """
    if not os.path.exists(target):
        os.makedirs(target)
    # FIXME: version checking

    candidates = [m for m in modules if name == m.name]
    if not candidates:
        raise ConcreateError("Cannot find requested module: '%s'" % name)

    for module in candidates:
        if version == module.get('version', None):
            return module

    if version:
        raise ConcreateError("Cannot find requested module: '%s', version:'%s'." % (name, version))

    # if we do not request any special version jus return random module
    return candidates[0]


def get_dependencies(descriptor, base_dir):
    """Go throug a list of dependencies in an image descriptor
    and fetch them.

    Arguments:
      descriptor - image descriptor
      base_dir - root directory for dependencies
    """
    logger.debug("Retrieving module repositories for '%s'" % (descriptor['name']))

    module_repositories = descriptor.get('modules', {}).get('repositories', [])

    if not module_repositories:
        logger.debug("No module repostiories specified in descriptor")
        return

    for repo in module_repositories:
        resource = Resource.new(repo, descriptor.directory)
        resource.copy(base_dir)


def discover_modules(repo_dir):
    """Looks through the directory trees for modules descriptor.
    When module is found, it create concreate.module.Module instance
    and add this instance to the concreate.module.modules list.
    """
    for modules_dir, _, files in os.walk(repo_dir):
        if 'module.yaml' in files:
            module = Module(os.path.join(modules_dir, 'module.yaml'))
            module.fetch_dependencies(repo_dir)
            logger.debug("Adding module '%s', path: '%s'" % (module.name, module.path))
            modules.append(module)


class Module(Descriptor):
    """Represents a module.

    Constructor arguments:
    descriptor_path: A path to module descriptor file.
    """
    def __init__(self, descriptor_path):
        self.descriptor = Descriptor(descriptor_path, 'module').process()
        self.name = self.descriptor['name']
        self.path = os.path.dirname(descriptor_path)

    def fetch_dependencies(self, repo_root):
        """ Processes modules dependencies and fetches them.

        Arguments:
        repo_root: A parent directory where repositories will be cloned in
        """
        get_dependencies(self.descriptor, repo_root)
