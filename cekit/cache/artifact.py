import glob
import yaml
import os
import uuid

from cekit.config import Config
from cekit.errors import CekitError
from cekit.crypto import SUPPORTED_HASH_ALGORITHMS, check_sum, get_sum

config = Config()


class ArtifactCache():
    """ Represents Artifact cache for cekit. All cached resource are saved into cache subdirectory
    of a Cekit 'work_dir'. All files are stored by random generated uuid with an yaml file
    indexing it.
    """

    def __init__(self):
        self._cache_dir = os.path.expanduser(
            os.path.join(config.get('common', 'work_dir'), 'cache'))
        if not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir)

    def _get_cache(self):
        cache = {}
        for index_file in glob.glob(os.path.join(self._cache_dir, '*.yaml')):
            with open(index_file, 'r') as file_:
                cache[os.path.basename(index_file)] = yaml.safe_load(file_)

        return cache

    def _update_cache(self, cache_entry, artifact_id):
        index_file = os.path.join(self._cache_dir, artifact_id + '.yaml')
        tmp_cache_file = index_file + str(os.getpid())
        with open(tmp_cache_file, 'w') as file_:
            yaml.dump(cache_entry, file_)
            os.rename(tmp_cache_file, index_file)

    def list(self):
        return self._get_cache()

    def add(self, artifact):
        if not set(SUPPORTED_HASH_ALGORITHMS).intersection(artifact):
            raise ValueError('Cannot cache Artifact without checksum')

        if self.is_cached(artifact):
            raise CekitError('Artifact is already cached')

        artifact_id = str(uuid.uuid4())

        artifact_file = os.path.expanduser(os.path.join(self._cache_dir, artifact_id))
        if not os.path.exists(artifact_file):
            artifact.guarded_copy(artifact_file)

        cache_entry = {'names': [artifact['name']],
                       'cached_path': artifact_file}

        for alg in SUPPORTED_HASH_ALGORITHMS:
            if alg in artifact:
                cache_entry.update({alg: artifact[alg]})

        self._update_cache(cache_entry, artifact_id)
        return artifact_id

    def delete(self, uuid):
        # check if artifact exists
        self._get_cache()
        os.remove(os.path.join(self._cache_dir, uuid))
        os.remove(os.path.join(self._cache_dir, uuid + '.yaml'))

    def get(self, artifact):
        for alg in SUPPORTED_HASH_ALGORITHMS:
            if alg in artifact:
                return self._find_artifact(alg, artifact[alg])
        raise CekitError('Artifact is not cached.')

    def _find_artifact(self, alg, chksum):
        cache = self._get_cache()
        for _, artifact in cache.items():
            if alg in artifact and artifact[alg] == chksum:
                return artifact

        raise CekitError('Artifact is not cached.')

    def is_cached(self, artifact):
        try:
            self.get(artifact)
            return True
        except CekitError:
            return False
