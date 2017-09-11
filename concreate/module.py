import os
import logging
import shutil

from concreate.descriptor import Descriptor
from concreate.errors import ConcreateError

logger = logging.getLogger('concreate')
# importable list of all modules
modules = []


def copy_modules_to_repository(src, dst):
    """ This is temporary function which copies modules
    located next to the image decriptor to common
    modules repository (args.target/repo)

    Arguments:
    src - path to the modules dir to be copied
    dst - destination of the modules directory
    """
    if os.path.exists(dst):
        # if the path exists here we should remove it
        shutil.rmtree(dst)
    if os.path.exists(src):
        logger.debug("Copying modules repo from '%s' to '%s'." % (src, dst))
        shutil.copytree(src, dst)


def copy_module_to_target(name, version, target):
    """ Copies a module from args.target/repo/... directory into
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
    for module in modules:
        if name == module.name:
            dest = os.path.join(target, name)
            logger.info('Preparing module %s' % module.name)
            if os.path.exists(dest):
                # FIXME check version
                return module
            shutil.copytree(module.path, dest)
            module.path = dest
            return module
    raise ConcreateError("Cannot find requested module: '%s'" % name)


def get_dependencies(descriptor, base_dir):
    """ Go throug a list of dependencies in an image descriptor
    and fetch them.

    Arguments:
      descriptor - image descriptor
      base_dir - root directory for dependencies
    """
    logger.debug("Retrieving dependencies for %s" % (descriptor['name']))
    if 'dependencies' not in descriptor:
        logger.debug("No dependencies specified in descriptor")
        return
    for dependency in descriptor['dependencies'].values():
        logger.debug("Downloading dependency %s" % (dependency.name))
        dependency.copy(base_dir)


def discover_modules(repo_dir):
    """ Looks through the directory trees for modules descriptor.
    When module is find, it create concreate.module.Module instance
    and add this instance to the concreate.module.modules list.
    """
    for modules_dir, _, files in os.walk(repo_dir):
        if 'module.yaml' in files:
            module = Module(os.path.join(modules_dir, 'module.yaml'))
            module.fetch_dependencies(repo_dir)
            modules.append(module)


class Module():
    """ Represents a module.

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
        if 'dependencies' in self.descriptor:
            get_dependencies(self.descriptor['dependencies'], repo_root)
