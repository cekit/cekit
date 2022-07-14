import importlib
import logging
import os
import shutil
import ssl
import subprocess
import sys
from typing import Mapping, Sequence
from urllib.parse import urlparse
from urllib.request import urlopen

import click
import yaml
from yaml.representer import SafeRepresenter

from cekit.config import Config
from cekit.errors import CekitError

logger = logging.getLogger("cekit")
config = Config()


class Map(dict):
    """
    Class to enable access via properties to dictionaries.
    """

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


# Make sure YAML can understand how to represent the Map object
SafeRepresenter.add_representer(Map, SafeRepresenter.represent_dict)


def download_file(url: str, destination: str) -> None:
    logger.debug("Downloading from '{}' as {}".format(url, destination))

    parsed_url = urlparse(url)

    if parsed_url.scheme == "file" or not parsed_url.scheme:
        if os.path.isdir(parsed_url.path):
            shutil.copytree(parsed_url.path, destination)
        else:
            shutil.copy(parsed_url.path, destination)
    elif parsed_url.scheme in ["http", "https"]:
        verify = config.get("common", "ssl_verify")
        if str(verify).lower() == "false":
            verify = False

        ctx = ssl.create_default_context()

        if not verify:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        res = urlopen(url, context=ctx)

        if res.getcode() != 200:
            raise CekitError("Could not download file from %s" % url)

        try:
            remote_size = int(res.getheader("Content-Length", "0"))
            chunk_size = 1048576  # 1 MB
            with open(destination, "wb") as f, click.progressbar(
                length=remote_size,
                label="Downloading {}".format(url.rsplit("/", 1)[-1]),
                show_percent=True,
                fill_char=(click.style("#", fg="green")),
                empty_char=(click.style("-", fg="white", dim=True)),
            ) as bar:
                while True:
                    chunk = res.read(chunk_size)
                    if not chunk:
                        break
                    bar.update(chunk_size)
                    f.write(chunk)
        except Exception as e:
            try:
                logger.debug(
                    "Removing incompletely downloaded '{}' file due to {}".format(
                        destination, e
                    )
                )
                os.remove(destination)
            except OSError:
                logger.warning(
                    "An error occurred while removing file '{}'".format(destination)
                )

            raise
    else:
        raise CekitError("Unsupported URL scheme: {}".format(url))


def load_descriptor(descriptor: str) -> dict:
    """parses descriptor and validate it against requested schema type

    Args:
      descriptor - yaml descriptor or path to a descriptor to be loaded.
      If a path is provided it must be an absolute path. In other case it's
      assumed that it is a yaml descriptor.

    Returns descriptor as a dictionary
    """

    if "-" == descriptor:
        descriptor = click.get_text_stream("stdin").read()
        logger.debug("Read from stdin: {}".format(descriptor))

    try:
        data = yaml.safe_load(descriptor)
    except Exception as ex:
        raise CekitError("Cannot load descriptor", ex)

    if isinstance(data, str):
        logger.debug("Reading descriptor from '{}' file...".format(descriptor))

        if os.path.exists(descriptor):
            with open(descriptor, "r") as fh:
                return yaml.safe_load(fh)

        raise CekitError(
            "Descriptor could not be found on the '{}' path, please check your arguments!".format(
                descriptor
            )
        )

    logger.debug("Reading descriptor directly...")

    return data


def decision(question):
    """Asks user for a question returning True/False answered"""
    return click.confirm(question, show_default=True)


def get_latest_image_version(image: str) -> str:
    inspect_cmd = [
        "/usr/bin/skopeo",
        "inspect",
        "--config",
        f"docker://{image}",
    ]
    auth = os.getenv("REGISTRY_AUTH_FILE")
    if auth:
        inspect_cmd.extend(["--authfile", auth])

    result = run_wrapper(inspect_cmd, True, f"Could not inspect container {image}")
    inspect_json = yaml.safe_load(result.stdout)["config"]
    tag = get_tag_from_inspect_struct(inspect_json)
    logger.debug(f"Found new tag {tag} for {image}")
    return f'{image.split(":")[0]}:{tag}'


def get_tag_from_inspect_struct(struct: Mapping) -> str:
    """Get the tag of a component from it's inspect struct

    An inspect struct is the parsed output of 'skopeo inspect'
    Generally it's a dict that contains a 'Labels' key that maps
    to a dict.

    Given the nvr "ubi8-minimal-8.1-279", the resulting tag will be
    "8.1-279".

    :param struct: Information about a container image.

    :return: The tag of the component.
    """
    labels = struct.get("Labels")
    if not isinstance(labels, Mapping):
        raise CekitError("Labels dict was not found in {}".format(struct))

    required_labels = {}
    missing_labels = []
    for label in ("version", "release"):
        if labels.get(label):
            required_labels[label] = labels[label]
        else:
            missing_labels.append(label)

    if missing_labels:
        raise CekitError(
            "The following labels, for image {}, were not set or empty".format(
                missing_labels
            )
        )

    return "{version}-{release}".format(**required_labels)


def get_brew_url(md5: str) -> str:
    logger.debug("Getting brew details for an artifact with '{}' md5 sum".format(md5))
    list_archives_cmd = [
        "/usr/bin/brew",
        "call",
        "--json-output",
        "listArchives",
        "checksum={}".format(md5),
        "type=maven",
    ]

    logger.debug("Executing '{}'.".format(" ".join(list_archives_cmd)))
    try:
        result = subprocess.run(
            list_archives_cmd, capture_output=True, check=True, text=True
        )
    except subprocess.CalledProcessError as ex:
        logger.error(
            "{} Command stdout is '{}' with stderr '{}'".format(
                ex, ex.stdout, ex.stderr
            )
        )
        if ex.output is not None and "AuthError" in ex.output:
            logger.warning(
                "Brew authentication failed, please make sure you have a valid Kerberos ticket"
            )
        raise CekitError("Could not fetch archives for checksum {}".format(md5), ex)

    archives = yaml.safe_load(result.stdout)

    if not archives:
        raise CekitError(
            "Artifact with md5 checksum {} could not be found in Brew".format(md5)
        )

    archive = archives[0]
    build_id = archive["build_id"]
    filename = archive["filename"]
    group_id = archive["group_id"]
    artifact_id = archive["artifact_id"]
    version = archive["version"]

    get_build_cmd = [
        "brew",
        "call",
        "--json-output",
        "getBuild",
        "buildInfo={}".format(build_id),
    ]

    result = run_wrapper(
        get_build_cmd, True, f"Could not fetch build {build_id} from Brew"
    )
    build = yaml.safe_load(result.stdout)

    build_states = ["BUILDING", "COMPLETE", "DELETED", "FAILED", "CANCELED"]

    # State 1 means: COMPLETE which is the only success state. Other states are:
    #
    # 'BUILDING': 0
    # 'COMPLETE': 1
    # 'DELETED': 2
    # 'FAILED': 3
    # 'CANCELED': 4
    if build["state"] != 1:
        raise CekitError(
            "Artifact with checksum {} was found in Koji metadata but the build is in incorrect state ({}) making "
            "the artifact not available for downloading anymore".format(
                md5, build_states[build["state"]]
            )
        )

    package = build["package_name"]
    release = build["release"]

    return (
        "http://download.devel.redhat.com/brewroot/packages/"
        + package
        + "/"
        + version.replace("-", "_")
        + "/"
        + release
        + "/maven/"
        + group_id.replace(".", "/")
        + "/"
        + artifact_id
        + "/"
        + version
        + "/"
        + filename
    )


def copy_recursively(source_directory: str, destination_directory: str) -> None:
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

        logger.debug("Copying '{}' to '{}'...".format(src, dst))

        if not os.path.isdir(os.path.dirname(dst)):
            os.makedirs(os.path.dirname(dst))

        if os.path.islink(src):
            os.symlink(os.readlink(src), dst)
        elif os.path.isdir(src):
            if sys.version_info[1] < 8:
                # Under pre Python 3.8 prefer dir_util over shutil as it doesn't throw an
                # exception for existing directories.
                from distutils import dir_util

                dir_util.copy_tree(src, dst, preserve_symlinks=True)
            else:
                shutil.copytree(src, dst, dirs_exist_ok=True, symlinks=True)
        else:
            shutil.copy2(src, dst)


def run_wrapper(
    cmd: Sequence[str],
    capture_output: bool,
    exception_message: str = "Exception running subprocess",
    check: bool = True,
) -> subprocess.CompletedProcess:
    """
    Useful wrapper around subprocess.run

    :param cmd: The command to execute
    :param capture_output: Whether to capture the output or not
    :param exception_message: An optional detailed exception message
    :param check: Whether to check the return code (defaults to True)
    :return: a CompletedProcess object
    """
    logger.debug("Executing '{}'.".format(" ".join(cmd)))
    try:
        # While it would be nicer to use
        #   result = subprocess.run(
        #        cmd, capture_output=capture_output, check=check, text=True
        #   )
        # capture_output and text are not available on Python 3.6
        stdout_capture = None
        stderr_capture = None
        if capture_output:
            stdout_capture = subprocess.PIPE
            stderr_capture = subprocess.PIPE
        result = subprocess.run(
            cmd,
            stdout=stdout_capture,
            stderr=stderr_capture,
            check=check,
            universal_newlines=True,
        )
    except subprocess.CalledProcessError as ex:
        logger.error(
            "{} Command stdout is '{}' with stderr '{}'".format(
                ex, ex.stdout, ex.stderr
            )
        )
        raise CekitError(exception_message, ex)
    if result.stdout:
        result.stdout = result.stdout.strip()
    if result.stderr:
        result.stderr = result.stderr.strip()
    return result


class Chdir(object):
    """Context manager for changing the current working directory"""

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
    KNOWN_OPERATING_SYSTEMS = ["fedora", "centos", "rhel"]

    # Set of core CEKit external dependencies.
    # Format is defined below, in the handle_dependencies() method
    EXTERNAL_CORE_DEPENDENCIES = {"git": {"package": "git", "executable": "git"}}

    def __init__(self):
        self.os_release = {}
        self.platform = None
        self.version = None

        os_release_path = "/etc/os-release"

        if os.path.exists(os_release_path):
            # Read the file containing operating system information
            with open(os_release_path, "r") as f:
                content = f.readlines()

            self.os_release = dict(
                [
                    ll.strip().split("=")
                    for ll in content
                    if not ll.isspace() and not ll.strip().startswith("#")
                ]
            )

            # Remove the quote character, if it's there
            for key in self.os_release.keys():
                self.os_release[key] = self.os_release[key].strip('"')

        if (
            not self.os_release
            or "ID" not in self.os_release
            or "NAME" not in self.os_release
            or "VERSION" not in self.os_release
            or "VERSION_ID" not in self.os_release
        ):
            logger.warning(
                "You are running CEKit on an unknown platform. External dependencies suggestions may not work!"
            )
            return

        self.platform = self.os_release["ID"]
        self.version = self.os_release["VERSION_ID"]

        if self.os_release["ID"] not in DependencyHandler.KNOWN_OPERATING_SYSTEMS:
            logger.warning(
                "You are running CEKit on an untested platform: {} {}. External dependencies "
                "suggestions will not work!".format(
                    self.os_release["NAME"], self.os_release["VERSION"]
                )
            )
            return

        logger.info(
            "You are running on known platform: {} {}".format(
                self.os_release["NAME"], self.os_release["VERSION"]
            )
        )

    def _handle_dependencies(self, dependencies: dict) -> None:
        """
        The dependencies provided is expected to be a dict in following format:

        {
            PACKAGE_ID: { 'package': PACKAGE_NAME, 'command': COMMAND_TO_TEST_FOR_PACKACGE_EXISTENCE },
        }

        Additionally, every package can contain platform specific information, for example:

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
        The platform may be a simple name like e.g. 'fedora' or combined with the OS version e.g. 'centos7'
        """

        if not dependencies:
            logger.debug("No dependencies found, skipping...")
            return

        for dependency in dependencies.keys():
            current_dependency = dependencies[dependency]

            package = current_dependency.get("package")
            library = current_dependency.get("library")
            executable = current_dependency.get("executable")

            if self.platform in current_dependency:
                package = current_dependency[self.platform].get("package", package)
                library = current_dependency[self.platform].get("library", library)
                executable = current_dependency[self.platform].get(
                    "executable", executable
                )
            platform_release = f"{self.platform}{self.version}"
            if platform_release in current_dependency:
                package = current_dependency[platform_release].get("package", package)
                library = current_dependency[platform_release].get("library", library)
                executable = current_dependency[platform_release].get(
                    "executable", executable
                )

            logger.debug(
                "Checking if '{}' dependency is provided...".format(dependency)
            )

            if library:
                if self._check_for_library(library):
                    logger.debug(
                        "Required CEKit library '{}' was found as a '{}' module!".format(
                            dependency, library
                        )
                    )
                    continue
                else:
                    msg = "Required CEKit library '{}' was not found; required module '{}' could not be found.".format(
                        dependency, library
                    )

                    # Library was not found, check if we have a hint
                    if (
                        package
                        and self.platform in DependencyHandler.KNOWN_OPERATING_SYSTEMS
                    ):
                        msg += " Try to install the '{}' package.".format(package)

                    raise CekitError(msg)

            if executable:
                if (
                    package
                    and self.platform in DependencyHandler.KNOWN_OPERATING_SYSTEMS
                ):
                    self._check_for_executable(dependency, executable, package)
                else:
                    self._check_for_executable(dependency, executable)

        logger.debug("All dependencies provided!")

    # noinspection PyMethodMayBeStatic
    def _check_for_library(self, library):
        library_found = False

        if importlib.util.find_spec(library):
            library_found = True

        return library_found

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
                logger.debug(
                    "CEKit dependency '{}' provided via the '{}' executable.".format(
                        dependency, file_path
                    )
                )
                return

        msg = "CEKit dependency: '{}' was not found, please provide the '{}' executable.".format(
            dependency, executable
        )

        if package:
            msg += (
                " To satisfy this requirement you can install the '{}' package.".format(
                    package
                )
            )

        raise CekitError(msg)

    def _is_program(self, path):
        if (
            os.path.exists(path)
            and os.access(path, os.F_OK | os.X_OK)
            and not os.path.isdir(path)
        ):
            return True

        return False

    def handle_core_dependencies(self):
        self._handle_dependencies(DependencyHandler.EXTERNAL_CORE_DEPENDENCIES)

        try:
            import certifi

            logger.warning(
                (
                    "The certifi library (https://certifi.io/) was found, depending on the operating "
                    + "system configuration this may result in certificate validation issues"
                )
            )
            logger.warning(
                "Certificate Authority (CA) bundle in use: '{}'".format(certifi.where())
            )
        except ImportError:
            pass

    def handle(self, o, params) -> None:
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
