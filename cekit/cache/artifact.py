import yaml
import os
import uuid


from cekit.errors import CekitError
from cekit import tools
from cekit.crypto import SUPPORTED_HASH_ALGORITHMS, check_sum, get_sum


class ArtifactCache():
    """ Represents Artifact cache for cekit. All cached reources are saved into cache subdirectory
    of a Cekit 'work_dir'. All files are stored by random generated uuid with an index.yaml file
    indexing it.
    """

    def __init__(self):
        self._cache_dir = os.path.expanduser(os.path.join(tools.cfg['common']['work_dir'], 'cache'))
        if not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir)
        self._cache_index_file = os.path.join(self._cache_dir, 'index.yaml')

    def _get_cache(self):
        if not os.path.exists(self._cache_index_file):
            return {}
        with open(self._cache_index_file, 'r') as file_:
            return yaml.safe_load(file_)

    def _update_cache(self, cache_index):
        with open(self._cache_index_file, 'w') as file_:
            yaml.dump(cache_index, file_)

    def list(self):
        return self._get_cache()

    def add(self, artifact):
        if not set(SUPPORTED_HASH_ALGORITHMS).intersection(artifact):
            raise ValueError('Cannot cache Artifact without checksum')

        artifact_id = str(uuid.uuid4())

        for alg in SUPPORTED_HASH_ALGORITHMS:
            if alg in artifact:
                self._index_artifact(artifact, artifact_id, alg, artifact[alg])
            else:
                self._index_artifact(artifact, artifact_id, alg)

        return artifact_id

    def _index_artifact(self, artifact, artifact_id, alg=None, chksum=None):
        artifact_file = os.path.expanduser(os.path.join(self._cache_dir, artifact_id))

        if not os.path.exists(artifact_file):
            artifact.guarded_copy(artifact_file)

        if chksum:
            if not check_sum(artifact_file, alg, chksum):
                raise CekitError('Artifact contains invalid checksum!')
        else:
            chksum = get_sum(artifact_file, alg)

        cache = self._get_cache()
        if artifact_id not in cache:
            cache[artifact_id] = {}

        cache[artifact_id].update({'names': [artifact['name']],
                                   alg: chksum,
                                   'cached_path': artifact_file})

        self._update_cache(cache)

    def delete(self, uuid):
        cache = self._get_cache()
        artifact = cache.pop(uuid)
        os.remove(os.path.expanduser(artifact['cached_path']))
        self._update_cache(cache)

    def get(self, artifact):
        for alg in SUPPORTED_HASH_ALGORITHMS:
            if alg in artifact:
                return self._find_artifact(alg, artifact[alg])
        raise CekitError('Artifact is not cached.')

    def _find_artifact(self, alg, chksum):
        cache = self._get_cache()
        for _, artifact in cache.items():
            if artifact[alg] == chksum:
                return artifact

        raise CekitError('Artifact is not cached.')

    def is_cached(self, artifact):
        try:
            self.get(artifact)
            return True
        except CekitError:
            return False
