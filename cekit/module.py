import os
import logging
import shutil

from cekit import tools
from cekit.descriptor import Module
from cekit.errors import CekitError

logger = logging.getLogger('cekit')
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
        raise CekitError("Cannot find requested module: '%s'" % name)

    for module in candidates:
        if not version or version == module.get('version', None):
            dest = os.path.join(target, module.name)

            # if module is already copied, check that the version is correct
            if os.path.exists(dest) and version:
                check_module_version(dest, version)

            if not os.path.exists(dest):
                logger.debug("Copying module '%s' from '%s' to: '%s'" % (name, module.path, dest))
                shutil.copytree(module.path, dest)
            return module

    raise CekitError("Cannot find requested module: '%s', version:'%s'." % (name, version))


def check_module_version(path, version):
    descriptor = Module(tools.load_descriptor(os.path.join(path, 'module.yaml')),
                        path,
                        os.path.dirname(os.path.abspath(os.path.join(path, 'module.yaml'))))
    if hasattr(descriptor, 'version') and descriptor.version != version:
        raise CekitError("Requested conflicting version '%s' of module '%s'" %
                     (version, descriptor['name']))


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
        logger.debug("No module repositories specified in descriptor")
        return

    for repo in module_repositories:
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        repo.copy(base_dir)
        discover_modules(os.path.join(base_dir, repo['name']))


def discover_modules(repo_dir):
    """Looks through the directory trees for modules descriptor.
    When module is found, it create cekit.module.Module instance
    and add this instance to the cekit.module.modules list.
    """
    for modules_dir, _, files in os.walk(repo_dir):
        if 'module.yaml' in files:
            module = Module(tools.load_descriptor(os.path.join(modules_dir, 'module.yaml')),
                            modules_dir,
                            os.path.dirname(os.path.abspath(os.path.join(modules_dir,
                                                                         'module.yaml'))))
            module.fetch_dependencies(repo_dir)
            logger.debug("Adding module '%s', path: '%s'" % (module.name, module.path))
            modules.append(module)
