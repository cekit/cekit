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


