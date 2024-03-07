import json
import logging
import os
import shutil
from abc import abstractmethod
from typing import Any, Dict, Optional, overload

from cekit.cekit_types import _T, PathType
from cekit.config import Config
from cekit.crypto import SUPPORTED_HASH_ALGORITHMS, check_sum
from cekit.descriptor import Descriptor
from cekit.errors import CekitError
from cekit.tools import Chdir, Map, download_file, get_brew_url, run_wrapper

logger = logging.getLogger("cekit")
config = Config()

RawResourceDescriptor = Dict[str, Any]

artifact_dest = "/tmp/artifacts/"


def create_resource(descriptor: RawResourceDescriptor, **kwargs) -> "Resource":
    """
    Module method responsible for instantiating proper resource object
    based on the provided descriptor.

    In most cases, only descriptor is required to create the object from descriptor.
    In case additional data is required, the kwargs 'dictionary' will be checked
    if the required key exists and will be used in the object constructor.
    """

    if "image" in descriptor:
        return _ImageContentResource(descriptor)

    if "path" in descriptor:
        directory = kwargs.pop("directory")

        if not directory:
            raise CekitError(
                (
                    "Internal error: cannot instantiate PathResource: {}, directory was not provided, "
                    + "please report it: https://github.com/cekit/cekit/issues"
                ).format(descriptor)
            )

        return _PathResource(descriptor, directory)

    # PNC first so it can have an optional URL component
    if "pnc_build_id" in descriptor:
        return _PncResource(descriptor)

    if "url" in descriptor:
        return _UrlResource(descriptor)

    if "git" in descriptor:
        return _GitResource(descriptor)

    if [x for x in SUPPORTED_HASH_ALGORITHMS if x in descriptor]:
        return _PlainResource(descriptor)

    raise CekitError(
        "Unable to determine whether a URL/Git/Plain or PNC resource so '{}' is not supported".format(
            descriptor
        )
    )


class Resource(Descriptor):
    """
    Base class for handling resources.

    In most cases resources are synonym to artifacts.
    """

    CHECK_INTEGRITY = True

    def __init__(self, descriptor: RawResourceDescriptor):
        # Schema must be provided by the implementing class
        if not self.schema:
            raise CekitError(f"Resource '{type(self).__name__}' has no schema defined")

        # Includes validation
        super(Resource, self).__init__(descriptor)

        # Make sure the we have 'name' set
        self._ensure_name(descriptor)
        # Make sure the we have 'target' set
        self._ensure_target(descriptor)
        # Add a single slash at the end of the 'dest' value
        self._normalize_dest(descriptor)
        # Convert the dictionary into a Map object for easier access
        self._descriptor = self.__to_map(descriptor)

        self.skip_merging = ["md5", "sha1", "sha256", "sha512"]

        # forwarded import to prevent circular imports
        from cekit.cache.artifact import ArtifactCache

        # TODO: This does not appear to be a circular import.

        self.cache: ArtifactCache = ArtifactCache()

    # TODO: Make `name` a property (probably on a parent class)

    # TODO: This seems to unnecessarily use name mangling
    @overload
    def __to_map(self, dictionary: dict) -> Map:
        pass

    @overload
    def __to_map(self, dictionary: _T) -> _T:
        pass

    def __to_map(self, dictionary):
        """
        Convert provided dictionary, recursively, into a Map object.

        This will make it possible to access nested elements
        via properties:

                res.git.url

        instead of:

                res.git['url]
        """
        if not isinstance(dictionary, dict):
            return dictionary

        converted = Map()

        for key in dictionary:
            converted[key] = self.__to_map(dictionary[key])

        return converted

    def __eq__(self, other):
        # All subclasses of Resource are considered same object type
        if isinstance(other, Resource):
            return self["name"] == other["name"]
        return NotImplemented

    def __ne__(self, other):
        # All subclasses of Resource are considered same object type
        if isinstance(other, Resource):
            return not self["name"] == other["name"]
        return NotImplemented

    def _ensure_name(self, descriptor: RawResourceDescriptor):
        """
        Makes sure the 'name' attribute exists.

        If it does not, a default value will be computed based on the implementation
        type of the resource class.
        """

        # If the 'name' key is present and there is a value, we have nothing to do
        if descriptor.get("name") is not None:
            return

        # Get the default value set for particular resource type
        default = self._get_default_name_value(descriptor)

        # If there is still no default, we need to fail, because 'name' is required.
        # If we ever get here, it is a bug and should be reported.
        if not default:
            raise CekitError(
                (
                    "Internal error: no value found for 'name' in '{}' artifact; unable to generate default value, "
                    + "please report it: https://github.com/cekit/cekit/issues"
                ).format(descriptor)
            )

        logger.warning(
            "No value found for 'name' in '{}' artifact; using auto-generated value of '{}'".format(
                json.dumps(descriptor, sort_keys=True), default
            )
        )

        descriptor["name"] = default

    def _ensure_target(self, descriptor: RawResourceDescriptor) -> None:
        if descriptor.get("target") is not None:
            return

        descriptor["target"] = self._get_default_target_value(descriptor)

    def _normalize_dest(self, descriptor: RawResourceDescriptor) -> None:
        """
        Make sure that the 'dest' value, if provided, does end with a single slash.
        """

        if descriptor.get("dest") is not None:
            descriptor["dest"] = os.path.normpath(descriptor.get("dest")) + "/"

    @abstractmethod
    def _get_default_name_value(self, descriptor: RawResourceDescriptor) -> str:
        """
        Returns default identifier value for particular class.

        This method must be overridden in classes extending Resource.
        Returned should be a string that will be be a unique identifier
        of the resource across thw whole image.
        """
        raise NotImplementedError(
            "Implement _get_default_name_value() for Resource: "
            + self.__module__
            + "."
            + type(self).__name__
        )

    def _get_default_target_value(self, descriptor: RawResourceDescriptor) -> str:
        return os.path.basename(descriptor.get("name"))

    @abstractmethod
    def _copy_impl(self, target: PathType) -> PathType:
        raise NotImplementedError(
            "Implement _copy_impl() for Resource: "
            + self.__module__
            + "."
            + type(self).__name__
        )

    def copy(self, target: PathType = os.getcwd()) -> PathType:
        if os.path.isdir(target):
            target = os.path.join(target, self.target)

        logger.info(f"Copying resource '{self.name}'...")

        if os.path.exists(target) and self.__verify(target):
            logger.debug(f"Local resource '{self.name}' exists and is valid")
            return target

        cached_resource = self.cache.cached(self)

        if cached_resource:
            shutil.copy(cached_resource["cached_path"], target)
            logger.info(f"Using cached artifact '{self.name}'.")

        else:
            try:
                self.cache.add(self)
                cached_resource = self.cache.get(self)
                shutil.copy(cached_resource["cached_path"], target)
                logger.info(f"Using cached artifact '{self.name}'.")
            except ValueError:
                return self.guarded_copy(target)

    def guarded_copy(self, target: PathType) -> PathType:
        try:
            self._copy_impl(target)
        except Exception as ex:
            logger.warning(
                "Cekit is not able to fetch resource '{}' automatically. "
                "Please use cekit-cache command to add this artifact manually.".format(
                    self.name
                )
            )

            if self.description:
                logger.info(self.description)

            # exception is fatal we be logged before Cekit dies
            raise CekitError(
                f"Error copying resource: '{self.name}'. See logs for more info."
            ) from ex

        if set(SUPPORTED_HASH_ALGORITHMS).intersection(self) and not self.__verify(
            target
        ):
            raise CekitError("Artifact checksum verification failed!")

        return target

    def __verify(self, target: PathType) -> bool:
        """Checks all defined check_sums for an artifact"""
        if not set(SUPPORTED_HASH_ALGORITHMS).intersection(self):
            logger.debug(f"Artifact '{self.name}' lacks any checksum definition.")
            return False
        if not Resource.CHECK_INTEGRITY:
            logger.info("Integrity checking disabled, skipping verification.")
            return True
        if os.path.isdir(target):
            logger.info("Target is directory, cannot verify checksum.")
            return True
        for algorithm in SUPPORTED_HASH_ALGORITHMS:
            if algorithm in self and self[algorithm]:
                if not check_sum(target, algorithm, self[algorithm]):
                    return False
        return True

    # TODO: This seems to unnecessarily use name mangling.
    def __substitute_cache_url(self, url: str) -> str:
        cache = config.get("common", "cache_url")

        if not cache:
            return url

        for algorithm in SUPPORTED_HASH_ALGORITHMS:
            if algorithm in self:
                logger.debug(
                    f"Using {algorithm} checksum to fetch artifacts from cacher"
                )

                url = (
                    cache.replace("#filename#", self.name)
                    .replace("#algorithm#", algorithm)
                    .replace("#hash#", self[algorithm])
                )

                logger.debug(f"Using cache url '{url}'")

        return url

    def _download_file(
        self, url: Optional[str], destination: PathType, use_cache=True
    ) -> None:
        """Downloads a file from url and save it as destination"""
        if use_cache:
            url = self.__substitute_cache_url(url)
        if not url:
            raise CekitError(
                f"Artifact {self.name} cannot be downloaded, no URL provided"
            )
        download_file(url, destination)


class _PathResource(Resource):
    """
    Documentation: http://docs.cekit.io/en/latest/descriptor/image.html#path-artifacts
    """

    SCHEMA = {
        "map": {
            "name": {"type": "str", "desc": "Key used to identify the resource"},
            "target": {"type": "str", "desc": "Target file name for the resource"},
            "dest": {
                "type": "str",
                "desc": "Destination directory inside of the container",
                "default": artifact_dest,
            },
            "description": {"type": "str", "desc": "Description of the resource"},
            "path": {
                "type": "str",
                "required": True,
                "desc": "Relative (suggested) or absolute path to the resource",
            },
            "md5": {"type": "str", "desc": "The md5 checksum of the resource"},
            "sha1": {"type": "str", "desc": "The sha1 checksum of the resource"},
            "sha256": {"type": "str", "desc": "The sha256 checksum of the resource"},
            "sha512": {"type": "str", "desc": "The sha512 checksum of the resource"},
        }
    }

    def __init__(self, descriptor: RawResourceDescriptor, directory: PathType):
        self.schema = _PathResource.SCHEMA

        super(_PathResource, self).__init__(descriptor)

        path = descriptor.get("path")

        # If the path is relative it's considered relative to the directory parameter
        if not os.path.isabs(path):
            self["path"] = os.path.join(directory, path)

    def _get_default_name_value(self, descriptor: RawResourceDescriptor) -> str:
        """
        Default identifier is the last part (most probably file name) of the URL.
        """
        return os.path.basename(descriptor.get("path"))

    def _copy_impl(self, target: PathType) -> PathType:
        if not os.path.exists(self.path):
            cache = config.get("common", "cache_url")

            # If cache_url is specified in Cekit configuration
            # file - try to fetch the 'path' artifact from cacher
            # even if it was not defined as 'url'.
            if cache:
                try:
                    self._download_file(self.path, target)
                    return target
                except Exception as ex:
                    raise CekitError(
                        f"Could not download resource '{self.name}' from cache"
                    ) from ex
            else:
                raise CekitError(
                    "Could not copy resource '%s', "
                    "source path does not exist. "
                    "Make sure you provided correct path" % self.name
                )

        logger.debug(f"Copying repository from '{self.path}' to '{target}'.")
        if os.path.isdir(self.path):
            shutil.copytree(self.path, target)
        else:
            shutil.copy2(self.path, target)
        return target


class _UrlResource(Resource):
    """
    Documentation: http://docs.cekit.io/en/latest/descriptor/image.html#url-artifacts
    """

    SCHEMA = {
        "map": {
            "name": {"type": "str", "desc": "Key used to identify the resource"},
            "target": {"type": "str", "desc": "Target file name for the resource"},
            "dest": {
                "type": "str",
                "desc": "Destination directory inside of the container",
                "default": artifact_dest,
            },
            "description": {"type": "str", "desc": "Description of the resource"},
            "url": {
                "type": "str",
                "required": True,
                "desc": "URL where the resource can be found",
            },
            "md5": {"type": "str", "desc": "The md5 checksum of the resource"},
            "sha1": {"type": "str", "desc": "The sha1 checksum of the resource"},
            "sha256": {"type": "str", "desc": "The sha256 checksum of the resource"},
            "sha512": {"type": "str", "desc": "The sha512 checksum of the resource"},
            "source-url": {"type": "str", "desc": "The source of the resource"},
            "source-md5": {
                "type": "str",
                "desc": "The md5 checksum of the source resource",
            },
            "source-sha1": {
                "type": "str",
                "desc": "The sha1 checksum of the source resource",
            },
            "source-sha256": {
                "type": "str",
                "desc": "The sha256 checksum of the source resource",
            },
        }
    }

    def __init__(self, descriptor: RawResourceDescriptor):
        self.schema = _UrlResource.SCHEMA

        super(_UrlResource, self).__init__(descriptor)

        # Normalize the URL
        self["url"] = descriptor.get("url").strip()

    # Avoid protected access warning
    def download_file(self, url: str, destination: PathType):
        return self._download_file(url, destination, use_cache=False)

    def _get_default_name_value(self, descriptor: RawResourceDescriptor) -> str:
        """
        Default identifier is the last part (most probably file name) of the URL.
        """
        return os.path.basename(descriptor.get("url"))

    def _copy_impl(self, target: PathType) -> PathType:
        try:
            self._download_file(self.url, target)
        except Exception:
            logger.debug(
                f"Cannot hit artifact: '{self.name}' via cache, trying directly."
            )
            self._download_file(self.url, target, use_cache=False)
        return target


class _GitResource(Resource):
    # TODO: This resource type is undocumented.

    SCHEMA = {
        "map": {
            "name": {"type": "str", "desc": "Key used to identify the resource"},
            "target": {"type": "str", "desc": "Target file name for the resource"},
            "description": {"type": "str", "desc": "Description of the resource"},
            "git": {
                "required": True,
                "map": {
                    "url": {
                        "type": "str",
                        "required": True,
                        "desc": "URL of the repository",
                    },
                    "ref": {
                        "type": "str",
                        "required": True,
                        "desc": "Reference to check out; could be branch, tag, etc",
                    },
                },
            },
        }
    }

    def __init__(self, descriptor):
        self.schema = _GitResource.SCHEMA

        super(_GitResource, self).__init__(descriptor)

    def _get_default_name_value(self, descriptor: RawResourceDescriptor):
        return os.path.basename(descriptor.get("git", {}).get("url")).split(".", 1)[0]

    def _copy_impl(self, target: PathType) -> PathType:
        cmd = ["git", "clone", self.git.url, target]
        run_wrapper(cmd, False, f"Could not clone from {self.git.url}")

        with Chdir(target):
            cmd = ["git", "checkout", self.git.ref]
            run_wrapper(cmd, False, f"Could not checkout from {self.git.ref}")

        return target


class _PlainResource(Resource):
    """
    Documentation: http://docs.cekit.io/en/latest/descriptor/image.html#plain-artifacts
    """

    SCHEMA = {
        "map": {
            "name": {
                "type": "str",
                "required": True,
                "desc": "Key used to identify the resource",
            },
            "target": {"type": "str", "desc": "Target file name for the resource"},
            "dest": {
                "type": "str",
                "desc": "Destination directory inside of the container",
                "default": artifact_dest,
            },
            "description": {"type": "str", "desc": "Description of the resource"},
            "md5": {"type": "str", "desc": "The md5 checksum of the resource"},
            "sha1": {"type": "str", "desc": "The sha1 checksum of the resource"},
            "sha256": {"type": "str", "desc": "The sha256 checksum of the resource"},
            "sha512": {"type": "str", "desc": "The sha512 checksum of the resource"},
            "source-url": {"type": "str", "desc": "The source of the resource"},
            "source-md5": {
                "type": "str",
                "desc": "The md5 checksum of the source resource",
            },
            "source-sha1": {
                "type": "str",
                "desc": "The sha1 checksum of the source resource",
            },
            "source-sha256": {
                "type": "str",
                "desc": "The sha256 checksum of the source resource",
            },
        }
    }

    def __init__(self, descriptor):
        self.schema = _PlainResource.SCHEMA

        super(_PlainResource, self).__init__(descriptor)

    def _copy_impl(self, target: PathType) -> PathType:
        # First of all try to download the file using cacher if specified
        if config.get("common", "cache_url"):
            try:
                self._download_file(url=None, destination=target)
                return target
            except Exception as e:
                logger.debug(str(e))
                logger.warning(
                    f"Could not download '{self.name}' artifact using cacher"
                )

        # Next option is to download it from Brew directly but only if the md5 checksum
        # is provided and we are running with the --redhat switch
        if self.md5 and config.get("common", "redhat"):
            logger.debug(
                f"Trying to download artifact '{self.name}' from Brew directly"
            )

            try:
                # Generate the URL
                url = get_brew_url(self.md5)
                # Use the URL to download the file
                self._download_file(url, target, use_cache=False)
                return target
            except Exception as e:
                logger.debug(str(e))
                logger.warning(f"Could not download artifact '{self.name}' from Brew")

        raise CekitError(f"Artifact {self.name} could not be found")

    def _get_default_name_value(self, descriptor: RawResourceDescriptor) -> str:
        return ""


class _ImageContentResource(Resource):
    """
    Class to cover artifacts that should be fetched from images.

    Main purpose of this type of resources are artifacts built as
    part of multi-stage builds. Other use case is where the artifact
    should be fetched from an already built image.

    Such a resource is represented in Dockerfile as:

        COPY --from=[IMAGE] [PATH] /tmp/artifacts/[NAME]

    Due to the nature of such resources, we're not able to validate
    checksums of such resources.
    """

    SCHEMA = {
        "map": {
            "name": {"type": "str", "desc": "Key used to identify the resource"},
            "target": {"type": "str", "desc": "Target file name for the resource"},
            "dest": {
                "type": "str",
                "desc": "Destination directory inside of the container",
                "default": "/tmp/artifacts/",
            },
            "description": {"type": "str", "desc": "Description of the resource"},
            "image": {
                "type": "str",
                "required": True,
                "desc": "Name of the image which holds the resource",
            },
            "path": {
                "type": "str",
                "required": True,
                "desc": "Path in the image under which the resource can be found",
            },
        }
    }

    def __init__(self, descriptor: RawResourceDescriptor):
        self.schema = _ImageContentResource.SCHEMA

        super(_ImageContentResource, self).__init__(descriptor)

    def _get_default_name_value(self, descriptor: RawResourceDescriptor) -> str:
        """
        Default identifier is the file name of the resource inside of the image.
        """
        return os.path.basename(descriptor.get("path"))

    def _copy_impl(self, target: PathType) -> PathType:
        """
        For stage artifacts, there is nothing to copy, because the artifact is located
        in an image that should be built in earlier stage of the image build process.
        """
        return target


class _PncResource(Resource):
    """
    Documentation: http://docs.cekit.io/en/latest/descriptor/image.html#pnc-artifacts
    """

    SCHEMA = {
        "map": {
            "name": {"type": "str", "desc": "Key used to identify the resource"},
            "target": {"type": "str", "desc": "Target file name for the resource"},
            "dest": {
                "type": "str",
                "desc": "Destination directory inside of the container",
                "default": artifact_dest,
            },
            "description": {"type": "str", "desc": "Description of the resource"},
            "pnc_artifact_id": {
                "type": "str",
                "required": True,
                "desc": "The ID of the artifact",
            },
            "pnc_build_id": {
                "type": "str",
                "required": True,
                "desc": "The ID of the build",
            },
            "url": {
                "type": "str",
                "desc": "Optional URL where the resource can be found",
            },
        }
    }

    def __init__(self, descriptor: RawResourceDescriptor):
        self.schema = _PncResource.SCHEMA

        super(_PncResource, self).__init__(descriptor)

    def _get_default_name_value(self, descriptor: RawResourceDescriptor) -> str:
        """
        Default identifier is the target file name.
        """
        return descriptor.get("target")

    def _copy_impl(self, target: PathType) -> PathType:
        """
        For PNC artifacts there is nothing to copy as the artifact is held remotely on PNC.
        """
        return target
