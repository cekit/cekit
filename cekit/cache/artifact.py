import glob
import os
import uuid
from typing import TYPE_CHECKING, Any, Dict, Union

import yaml

from cekit.cekit_types import PathType
from cekit.config import Config
from cekit.crypto import SUPPORTED_HASH_ALGORITHMS, get_sum
from cekit.errors import CekitError

if TYPE_CHECKING:
    from cekit.descriptor import Resource

CONFIG = Config()


class ArtifactCache:
    """
    Represents Artifact cache for cekit. All cached resource are saved into cache subdirectory
    of a Cekit 'work_dir'. All files are stored by random generated uuid with an yaml file
    indexing it.
    """

    def __init__(self):
        self.cache_dir: PathType = os.path.expanduser(
            os.path.join(CONFIG.get("common", "work_dir"), "cache")
        )
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _get_cache(self) -> Dict[str, Any]:
        cache = {}
        for index_file in glob.glob(os.path.join(self.cache_dir, "*.yaml")):
            with open(index_file, "r") as file_:
                cache[os.path.basename(index_file)] = yaml.safe_load(file_)

        return cache

    def _update_cache(self, cache_entry: Any, artifact_id: str) -> None:
        index_file = os.path.join(self.cache_dir, artifact_id + ".yaml")
        tmp_cache_file = index_file + str(os.getpid())
        with open(tmp_cache_file, "w") as file_:
            yaml.safe_dump(cache_entry, file_)
            os.rename(tmp_cache_file, index_file)

    def list(self) -> Dict[str, Any]:
        return self._get_cache()

    def add(self, artifact: "Resource"):
        # TODO: This line works, but it really is non-obvious why.
        if not set(SUPPORTED_HASH_ALGORITHMS).intersection(artifact):
            raise ValueError("Cannot cache artifact without checksum")

        if self.cached(artifact):
            raise CekitError("Artifact is already cached!")

        artifact_id: str = str(uuid.uuid4())

        artifact_file = os.path.expanduser(os.path.join(self.cache_dir, artifact_id))
        if not os.path.exists(artifact_file):
            artifact.guarded_copy(artifact_file)

        # TODO: replace this with a specific type/class
        cache_entry = {"names": [artifact["name"]], "cached_path": artifact_file}

        # We should populate the cache entry with checksums for all supported algorithms
        for alg in SUPPORTED_HASH_ALGORITHMS:
            cache_entry.update({alg: get_sum(artifact_file, alg)})

        self._update_cache(cache_entry, artifact_id)
        return artifact_id

    def delete(self, artifact_uuid):
        # check if artifact exists
        # TODO: This doesn't actually appear to check anything
        self._get_cache()
        os.remove(os.path.join(self.cache_dir, artifact_uuid))
        os.remove(os.path.join(self.cache_dir, artifact_uuid + ".yaml"))

    def get(self, artifact: "Resource"):
        for alg in SUPPORTED_HASH_ALGORITHMS:
            if alg in artifact:
                return self._find_artifact(alg, artifact[alg])
        raise CekitError("Artifact is not cached.")

    def _find_artifact(self, alg: str, chksum: str):
        cache = self._get_cache()
        for _, artifact in cache.items():
            if alg in artifact and artifact[alg] == chksum:
                return artifact

        raise CekitError("Artifact is not cached.")

    # TODO: Make this return Optional[Resource] instead of Union[Resource, bool]
    def cached(self, artifact: "Resource") -> Union["Resource", bool]:
        try:
            return self.get(artifact)
        except CekitError:
            return False
