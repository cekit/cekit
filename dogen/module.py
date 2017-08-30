import os
import subprocess
import logging
import shutil

from dogen.descriptor import Descriptor
from dogen.errors import DogenError
from dogen import tools

logger = logging.getLogger('dogen')
# importable list of all modules
modules = []


def copy_image_module_to_repository(src, dst):
    """ This is temporary function which copies modules
    located next to the image decriptor to common
    modules repository (args.target/repo)

    Arguments:
    src - path to the modules dir to be copied
    dst - destination of the modules directory
    """
    if os.path.exists(dst):
        return
    if os.path.exists(src):
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
    raise DogenError("Cannot find requested module: '%s'" % name)

def get_image_dependencies(descriptor, base_dir):
    """ Go throug a list of dependencies in an image descriptor
    and fetch them.

    Arguments:
      descriptor - image descriptor
      base_dir - root directory for dependencies
    """
    if 'dependencies' not in descriptor:
        return
    for dependency in descriptor['dependencies']:
        fetch_module_repository(dependency['url'],
                                dependency['ref'],
                                base_dir)

def fetch_module_repository(url, ref, base_dir):
    """ Clones a git repository containing cct modules.
    Repository is clonde to args.target/repo/name-ref directory

    Arguments:
    url: url for git repository of modules
    ref: git reference to checkout
    base_dir: parent directory where git repo will be cloned

    Returns directory where module was cloned
    """
    try:
        target_dir = os.path.join(base_dir,
                                  "%s-%s" % (os.path.basename(url), ref))
        if os.path.exists(target_dir):
            return target_dir
        # FIXME if url is local path - lets copy it instead (for local development)
        cmd = ['git', 'clone', '--depth', '1', url, target_dir, '-b', ref]
        logger.debug("Running '%s'" % ' '.join(cmd))
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return target_dir
    except Exception as ex:
        # exception is fatal we be logged before Dogen dies
        raise DogenError('Cannot fetch module repository: %s' % ex, ex)


def discover_modules(repo_dir):
    """ Looks through the directory trees for modules descriptor.
    When module is find, it create dogen.module.Module instance
    and add this instance to the dogen.module.modules list.
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
        # FIXME schema check
        self.name = self.descriptor['name']
        self.path = os.path.dirname(descriptor_path)

    def fetch_dependencies(self, repo_root):
        """ Processes modules dependencies and fetches them.

        Arguments:
        repo_root: A parent directory where repositories will be cloned in
        """
        if 'dependencies' not in self.descriptor:
            return
        for dependency in self.descriptor['dependencies']:
            repo_dir = fetch_module_repository(dependency['url'],
                                               dependency['ref'],
                                               repo_root)
            discover_modules(repo_dir)
