import logging
import os
import shutil
import sys
import subprocess
import yaml

from cekit.errors import CekitError

logger = logging.getLogger('cekit')


def cleanup(target):
    """ Prepates target/image directory to be regenerated."""
    dirs_to_clean = [os.path.join(target, 'image', 'modules'),
                     os.path.join(target, 'image', 'repos'),
                     os.path.join(target, 'repo')]
    for d in dirs_to_clean:
        if os.path.exists(d):
            logger.debug("Removing dirty directory: '%s'" % d)
            shutil.rmtree(d)


def load_descriptor(descriptor):
    """ parses descriptor and validate it against requested schema type

    Args:
      descriptor - yaml descriptor or path to a descriptor to be loaded

    Returns descriptor as a dictionary
    """
    if not os.path.exists(descriptor):
        logger.debug("Descriptor path '%s' doesn't exists, trying to parse it directly."
                     % descriptor)
        try:
            return yaml.safe_load(descriptor)
        except Exception as ex:
            raise CekitError('Cannot load descriptor.', ex)

    logger.debug("Loading descriptor from path '%s'." % descriptor)

    with open(descriptor, 'r') as fh:
        return yaml.safe_load(fh)


def decision(question):
    """Asks user for a question returning True/False answed"""
    if sys.version_info[0] < 3:
        if raw_input("\n%s [Y/n] " % question) in ["", "y", "Y"]:
            return True
    else:
        if input("\n%s [Y/n] " % question) in ["", "y", "Y"]:
            return True

    return False


def get_brew_url(md5):
    try:
        logger.debug("Getting brew details for an artifact with '%s' md5 sum" % md5)
        list_archives_cmd = ['brew', 'call', '--json-output', 'listArchives',
                             'checksum=%s' % md5, 'type=maven']
        logger.debug("Executing '%s'." % " ".join(list_archives_cmd))
        archive_yaml = yaml.safe_load(subprocess.check_output(list_archives_cmd))

        if not archive_yaml:
            raise CekitError("Artifact with md5 checksum %s could not be found in Brew" % md5)

        archive = archive_yaml[0]
        build_id = archive['build_id']
        filename = archive['filename']
        group_id = archive['group_id']
        artifact_id = archive['artifact_id']
        version = archive['version']

        get_build_cmd = ['brew', 'call', '--json-output', 'getBuild', 'buildInfo=%s' % build_id]
        logger.debug("Executing '%s'" % " ".join(get_build_cmd))
        build = yaml.safe_load(subprocess.check_output(get_build_cmd))
        package = build['package_name']
        release = build['release']

        url = 'http://download.devel.redhat.com/brewroot/packages/' + package + '/' + \
            version.replace('-', '_') + '/' + release + '/maven/' + \
            group_id.replace('.', '/') + '/' + artifact_id.replace('.', '/') + '/' + \
            version + '/' + filename
    except subprocess.CalledProcessError as ex:
        logger.error("Can't fetch artifacts details from brew: '%s'." %
                     ex.output)
        raise ex
    return url


class Chdir(object):
    """ Context manager for changing the current working directory """

    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

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

    # List of operating system families on which Cekit is known to work.
    # It may work on other operating systems too, but it was not tested.
    KNOWN_OPERATING_SYSTEMS = ['fedora', 'centos', 'rhel']

    # Set of core Cekit external dependencies.
    # Format is defined below, in the handle_dependencies() method
    EXTERNAL_CORE_DEPENDENCIES = {
        'git': {
            'package': 'git',
            'command': 'git --version'
        }
    }

    def __init__(self):
        os_release_path = "/etc/os-release"

        if (os.path.exists(os_release_path)):
            # Read the file containing operating system information
            self.os_release = dict(l.strip().split('=') for l in open(os_release_path))

            # Remove the quote character, if it's there
            for key in self.os_release.keys():
                self.os_release[key] = self.os_release[key].strip('"')
        else:
            logger.warning(
                "You are running Cekit on an unknown platform. External dependencies suggestions may not work!")
            return

        if self.os_release['ID'] not in DependencyHandler.KNOWN_OPERATING_SYSTEMS:
            logger.warning(
                "You are running Cekit on an untested platform: {} {}. External dependencies suggestions will not work!".format(self.os_release['NAME'], self.os_release['VERSION']))
            return

        DependencyHandler.handle_dependencies(
            DependencyHandler.EXTERNAL_CORE_DEPENDENCIES, self.os_release['ID'])

    @staticmethod
    def handle_dependencies(dependencies, platform):
        """
        The dependencies provided is expected to be a dict in following format:

        {
            PACKAGE_ID: { 'package': PACKAGE_NAME, 'command': COMMAND_TO_TEST_FOR_PACKACGE_EXISTENCE },
        }

        Additionally every package can contain platform specific information, for example:

        {
            'git': {
                'package': 'git',
                'command': 'git --version',
                'fedora': {
                    'package': 'git-latest',
                    'command': 'git --version',
                }
            }
        }

        If the platform on which Cekit is currently running is available, it takes precedence before
        defaults.
        """

        for dependency in dependencies.keys():
            current_dependency = dependencies[dependency]

            package = current_dependency.get('package')
            library = current_dependency.get('library')
            command = current_dependency.get('command')

            if platform in current_dependency:
                package = current_dependency[platform].get('package', package)
                library = current_dependency[platform].get('library', library)
                command = current_dependency[platform].get('command', command)

            logger.debug("Checking if '{}' dependency is provided...".format(dependency))

            library_found = False

            if library:
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

                if library_found:
                    logger.debug("Required Cekit library '{}' was found as a '{}' module!".format(
                        dependency, library))
                    continue
                else:
                    # Library was not found, check if we have a hint
                    if package and platform in DependencyHandler.KNOWN_OPERATING_SYSTEMS:
                        raise CekitError("Required Cekit library '{}' could not be found. Try to install the '{}' package.".format(
                            dependency, package))

            if package and platform in DependencyHandler.KNOWN_OPERATING_SYSTEMS:
                try:
                    # TODO: Do not use shell here!
                    subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
                    logger.debug("Cekit dependency '{}' provided via the '{}' package.".format(
                        dependency, package))
                    continue
                except subprocess.CalledProcessError:
                    raise CekitError(
                        "Cekit dependency: '{}' was not found, please install the '{}' package.".format(dependency, package))

        logger.debug("All dependencies provided!")

    def handle(self, o):
        """
        Handles dependencies from selected object. If the object has 'dependencies' method,
        it will be called to retrieve a set of dependencies to check for.
        """

        if not o:
            return

        # Get the class of the object
        clazz = type(o)

        # Check if the method or variable of 'dependencies' name exists
        dependencies = getattr(clazz, "dependencies", None)

        # Check if we have a method
        if callable(dependencies):
            # Execute that method to get list of dependecies and try to handle them
            DependencyHandler.handle_dependencies(clazz.dependencies(), self.os_release['ID'])
