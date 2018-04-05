import logging
import yaml
import os

from cekit.generator.base import Generator

logger = logging.getLogger('cekit')


class OSBSGenerator(Generator):

    def __init__(self, descriptor_path, target, builder, overrides):
        self._wipe = False
        super(OSBSGenerator, self).__init__(descriptor_path, target, builder, overrides)

    def _prepare_repository_odcs_pulp(self, repo):
        content_set_f = os.path.join(self.target, 'image', 'content_sets.yaml')
        content_set = {}

        if os.path.exists(content_set_f):
            with open(content_set_f, 'r') as _file:
                content_set = yaml.safe_load(_file)

        cur_repos = content_set.get('x86_64', [])
        if self._wipe:
            cur_repos = []
            self._wipe = False

        if repo['repository'] not in cur_repos:
            cur_repos.append(repo['repository'])

        content_set['x86_64'] = cur_repos
        with open(content_set_f, 'w') as _file:
            yaml.dump(content_set, _file)
        return False
