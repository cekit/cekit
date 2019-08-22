import logging
import os
import shutil
import subprocess
import sys

import click

import yaml
from yaml.representer import SafeRepresenter

from cekit.errors import CekitError

try:
    basestring
except NameError:
    basestring = str

LOGGER = logging.getLogger('cekit')


class Map(dict):
    """
    Class to enable access via properties to dictionaries.
    """

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


# Make sure YAML can understand how to represent the Map object
SafeRepresenter.add_representer(Map, SafeRepresenter.represent_dict)


def load_descriptor(descriptor):
    """ parses descriptor and validate it against requested schema type

    Args:
      descriptor - yaml descriptor or path to a descriptor to be loaded.
      If a path is provided it must be an absolute path. In other case it's
      assumed that it is a yaml descriptor.

    Returns descriptor as a dictionary
    """

    try:
        data = yaml.safe_load(descriptor)
    except Exception as ex:
        raise CekitError('Cannot load descriptor', ex)

    if isinstance(data, basestring):
        LOGGER.debug("Reading descriptor from '{}' file...".format(descriptor))

        if os.path.exists(descriptor):
            with open(descriptor, 'r') as fh:
                return yaml.safe_load(fh)

        raise CekitError(
            "Descriptor could not be found on the '{}' path, please check your arguments!".format(descriptor))

    LOGGER.debug("Reading descriptor directly...")

    return data


def decision(question):
    """Asks user for a question returning True/False answed"""
    return click.confirm(question, show_default=True)


def get_brew_url(md5):
    try:
        LOGGER.debug("Getting brew details for an artifact with '{}' md5 sum".format(md5))
        list_archives_cmd = ['/usr/bin/brew', 'call', '--json-output', 'listArchives',
                             "checksum={}".format(md5), 'type=maven']
        LOGGER.debug("Executing '{}'.".format(" ".join(list_archives_cmd)))

        try:
            json_archives = subprocess.check_output(list_archives_cmd).strip().decode("utf8")
        except subprocess.CalledProcessError as ex:
            if ex.output is not None and 'AuthError' in ex.output:
                LOGGER.warning(
                    "Brew authentication failed, please make sure you have a valid Kerberos ticket")
            raise CekitError("Could not fetch archives for checksum {}".format(md5), ex)

        archives = yaml.safe_load(json_archives)

        if not archives:
            raise CekitError("Artifact with md5 checksum {} could not be found in Brew".format(md5))

        archive = archives[0]
        build_id = archive['build_id']
        filename = archive['filename']
        group_id = archive['group_id']
        artifact_id = archive['artifact_id']
        version = archive['version']

        get_build_cmd = ['brew', 'call', '--json-output',
                         'getBuild', "buildInfo={}".format(build_id)]

        LOGGER.debug("Executing '{}'".format(" ".join(get_build_cmd)))

        try:
            json_build = subprocess.check_output(get_build_cmd).strip().decode("utf8")
        except subprocess.CalledProcessError as ex:
            raise CekitError("Could not fetch build {} from Brew".format(build_id), ex)

        build = yaml.safe_load(json_build)

        build_states = ['BUILDING', 'COMPLETE', 'DELETED', 'FAILED', 'CANCELED']

        # State 1 means: COMPLETE which is the only success state. Other states are:
        #
        # 'BUILDING': 0
        # 'COMPLETE': 1
        # 'DELETED': 2
        # 'FAILED': 3
        # 'CANCELED': 4
        if build['state'] != 1:
            raise CekitError(
                "Artifact with checksum {} was found in Koji metadata but the build is in incorrect state ({}) making "
                "the artifact not available for downloading anymore".format(md5, build_states[build['state']]))

        package = build['package_name']
        release = build['release']

        url = 'http://download.devel.redhat.com/brewroot/packages/' + package + '/' + \
            version.replace('-', '_') + '/' + release + '/maven/' + \
            group_id.replace('.', '/') + '/' + \
            artifact_id + '/' + version + '/' + filename
    except subprocess.CalledProcessError as ex:
        LOGGER.error("Can't fetch artifacts details from brew: '{}'.".format(
                     ex.output))
        raise ex
    return url


def copy_recursively(source_directory, destination_directory):
    """
    Copies contents of a directory to selected target location (also a directory).
    the specific source file to destination.

    If the source directory contains a directory, it will copy all the content recursively.
    Symlinks are preserved (not followed).

    The destination directory tree will be created if it does not exist.
    """

    # If the source directory does not exists, return
    if not os.path.isdir(source_directory):
        return

    # Iterate over content in the source directory
    for name in os.listdir(source_directory):
        src = os.path.join(source_directory, name)
        dst = os.path.join(destination_directory, name)

        LOGGER.debug("Copying '{}' to '{}'...".format(src, dst))

        if not os.path.isdir(os.path.dirname(dst)):
            os.makedirs(os.path.dirname(dst))

        if os.path.islink(src):
            os.symlink(os.readlink(src), dst)
        elif os.path.isdir(src):
            shutil.copytree(src, dst, symlinks=True)
        else:
            shutil.copy2(src, dst)


class Chdir(object):
    """ Context manager for changing the current working directory """

    def __init__(self, new_path):
        self.newPath = os.path.expanduser(new_path)
        self.savedPath = None

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)


class DependencyHandler(object):
    """
    External dependency manager. Understands on what platform are we currently
    running and what dependencies are required to be installed to satisfy the
    requirements.
    """

    # List of operating system families on which CEKit is known to work.
    # It may work on other operating systems too, but it was not tested.
    KNOWN_OPERATING_SYSTEMS = ['fedora', 'centos', 'rhel']

    # Set of core CEKit external dependencies.
    # Format is defined below, in the handle_dependencies() method
    EXTERNAL_CORE_DEPENDENCIES = {
        'git': {
            'package': 'git',
            'executable': 'git'
        }
    }

    def __init__(self):
        self.os_release = {}
        self.platform = None

        os_release_path = "/etc/os-release"

        if os.path.exists(os_release_path):
            # Read the file containing operating system information
            with open(os_release_path, 'r') as f:
                content = f.readlines()

            self.os_release = dict([l.strip().split('=')
                                    for l in content if not l.isspace() and not l.strip().startswith('#')])

            # Remove the quote character, if it's there
            for key in self.os_release.keys():
                self.os_release[key] = self.os_release[key].strip('"')

        if not self.os_release or 'ID' not in self.os_release or 'NAME' not in self.os_release or 'VERSION' not in self.os_release:
            LOGGER.warning(
                "You are running CEKit on an unknown platform. External dependencies suggestions may not work!")
            return

        self.platform = self.os_release['ID']

        if self.os_release['ID'] not in DependencyHandler.KNOWN_OPERATING_SYSTEMS:
            LOGGER.warning(
                "You are running CEKit on an untested platform: {} {}. External dependencies "
                "suggestions will not work!".format(self.os_release['NAME'], self.os_release['VERSION']))
            return

        LOGGER.info("You are running on known platform: {} {}".format(
            self.os_release['NAME'], self.os_release['VERSION']))

    def _handle_dependencies(self, dependencies):
        """
        The dependencies provided is expected to be a dict in following format:

        {
            PACKAGE_ID: { 'package': PACKAGE_NAME, 'command': COMMAND_TO_TEST_FOR_PACKACGE_EXISTENCE },
        }

        Additionally every package can contain platform specific information, for example:

        {
            'git': {
                'package': 'git',
                'executable': 'git',
                'fedora': {
                    'package': 'git-latest'
                }
            }
        }

        If the platform on which CEKit is currently running is available, it takes precedence before
        defaults.
        """

        if not dependencies:
            LOGGER.debug("No dependencies found, skipping...")
            return

        for dependency in dependencies.keys():
            current_dependency = dependencies[dependency]

            package = current_dependency.get('package')
            library = current_dependency.get('library')
            executable = current_dependency.get('executable')

            if self.platform in current_dependency:
                package = current_dependency[self.platform].get('package', package)
                library = current_dependency[self.platform].get('library', library)
                executable = current_dependency[self.platform].get('executable', executable)

            LOGGER.debug("Checking if '{}' dependency is provided...".format(dependency))

            if library:
                if self._check_for_library(library):
                    LOGGER.debug("Required CEKit library '{}' was found as a '{}' module!".format(
                        dependency, library))
                    continue
                else:
                    msg = "Required CEKit library '{}' was not found; required module '{}' could not be found.".format(
                        dependency, library)

                    # Library was not found, check if we have a hint
                    if package and self.platform in DependencyHandler.KNOWN_OPERATING_SYSTEMS:
                        msg += " Try to install the '{}' package.".format(package)

                    raise CekitError(msg)

            if executable:
                if package and self.platform in DependencyHandler.KNOWN_OPERATING_SYSTEMS:
                    self._check_for_executable(dependency, executable, package)
                else:
                    self._check_for_executable(dependency, executable)

        LOGGER.debug("All dependencies provided!")

    # pylint: disable=R0201
    def _check_for_library(self, library):
        library_found = False

        if sys.version_info[0] < 3:
            import imp
            try:
                imp.find_module(library)
                library_found = True
            except ImportError:
                pass
        else:
            import importlib
            if importlib.util.find_spec(library):
                library_found = True

        return library_found

    # pylint: disable=no-self-use
    def _check_for_executable(self, dependency, executable, package=None):
        if os.path.isabs(executable):
            if self._is_program(executable):
                return True
            else:
                return False

        path = os.environ.get("PATH", os.defpath)
        path = path.split(os.pathsep)

        for directory in path:
            file_path = os.path.join(os.path.normcase(directory), executable)

            if self._is_program(file_path):
                LOGGER.debug("CEKit dependency '{}' provided via the '{}' executable.".format(
                    dependency, file_path))
                return

        msg = "CEKit dependency: '{}' was not found, please provide the '{}' executable.".format(
            dependency, executable)

        if package:
            msg += " To satisfy this requirement you can install the '{}' package.".format(package)

        raise CekitError(msg)

    def _is_program(self, path):
        if os.path.exists(path) and os.access(path, os.F_OK | os.X_OK) and not os.path.isdir(path):
            return True

        return False

    def handle_core_dependencies(self):
        self._handle_dependencies(
            DependencyHandler.EXTERNAL_CORE_DEPENDENCIES)

        try:
            import certifi  # pylint: disable=unused-import
            LOGGER.warning(("The certifi library (https://certifi.io/) was found, depending on the operating " +
                            "system configuration this may result in certificate validation issues"))
            LOGGER.warning("Certificate Authority (CA) bundle in use: '{}'".format(certifi.where()))
        except ImportError:
            pass

    def handle(self, o, params):
        """
        Handles dependencies from selected object. If the object has 'dependencies' method,
        it will be called to retrieve a set of dependencies to check for.
        :param params:
        """

        if not o:
            return

        # Get the class of the object
        clazz = type(o)

        for var in [clazz, o]:
            # Check if a static method or variable 'dependencies' exists
            dependencies = getattr(var, "dependencies", None)

            if not dependencies:
                continue

            # Check if we have a method
            if callable(dependencies):
                # Execute that method to get list of dependencies and try to handle them
                self._handle_dependencies(o.dependencies(params))
                return
