import logging
import yaml
import os

from cekit.generator.base import Generator

logger = logging.getLogger('cekit')


class OSBSGenerator(Generator):

    def __init__(self, descriptor_path, target, builder, overrides, params):
        self._wipe = False
        super(OSBSGenerator, self).__init__(descriptor_path, target, builder, overrides, params)

    def _prepare_repository_odcs_pulp(self, repo):
        self._prepare_content_set_yaml(repo['odcs']['pulp'])
        self._prepate_odcs_container_yaml()

    def _prepare_content_set_yaml(self, repo_name):
        content_set_f = os.path.join(self.target, 'image', 'content_sets.yml')
        content_set = {}

        if os.path.exists(content_set_f):
            with open(content_set_f, 'r') as _file:
                content_set = yaml.safe_load(_file)

        cur_repos = content_set.get('x86_64', [])
        if self._wipe:
            cur_repos = []
            self._wipe = False

        if repo_name not in cur_repos:
            cur_repos.append(repo_name)

        content_set['x86_64'] = cur_repos

        if not os.path.exists(os.path.dirname(content_set_f)):
            os.makedirs(os.path.dirname(content_set_f))

        with open(content_set_f, 'w') as _file:
            yaml.dump(content_set, _file)

        # check the cotnianter.yaml and pulp true
        return False

    def _prepate_odcs_container_yaml(self):
        container_f = os.path.join(self.target, 'image', 'container.yaml')
        container = {}

        if os.path.exists(container_f):
            with open(container_f, 'r') as _file:
                container = yaml.safe_load(_file)

        container['compose'] = {'pulp_repos': True}

        with open(container_f, 'w') as _file:
            yaml.dump(container, _file)

    def _prepare_repository_rpm(self, repo):
        # no special handling is needed here, everything is in template
        pass
