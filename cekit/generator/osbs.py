import logging
import yaml
import os

from cekit import tools
from cekit.generator.base import Generator

logger = logging.getLogger('cekit')

RHEL_REPOS_MAP = {}
RHEL_REPOS_MAP['rhel-7-server-rpms'] = 'rhel-7-for-power-le-rpms'
RHEL_REPOS_MAP['rhel-7-extras-rpms'] = 'rhel-7-for-power-le-extras-rpms'
RHEL_REPOS_MAP['rhel-server-rhscl-7-rpms'] = 'rhel-7-server-for-power-le-rhscl-rpms'


class OSBSGenerator(Generator):
    def __init__(self, descriptor_path, target, builder, overrides, params):
        self._wipe = True
        super(OSBSGenerator, self).__init__(descriptor_path, target, builder, overrides, params)

        # wipe old contianer and content_set config files
        self._content_set_f = os.path.join(self.target, 'image', 'content_sets.yml')
        if os.path.exists(self._content_set_f):
            os.remove(self._content_set_f)
        self._container_f = os.path.join(self.target, 'image', 'container.yaml')
        if os.path.exists(self._container_f):
            os.remove(self._container_f)

    def _prepare_repository_odcs_pulp(self, repo):
        self._prepare_content_set_yaml(repo['odcs']['pulp'])
        self._prepate_odcs_container_yaml()

    def _prepare_content_set_yaml(self, repo_name):
        content_set = {}

        if os.path.exists(self._content_set_f):
            with open(self._content_set_f, 'r') as _file:
                content_set = yaml.safe_load(_file)

        cur_repos = content_set.get('x86_64', [])
        if self._wipe:
            cur_repos = []
            self._wipe = False

        if repo_name not in cur_repos:
            cur_repos.append(repo_name)

        content_set['x86_64'] = cur_repos
        if tools.cfg['common']['redhat']:
            ppc_repos = []
            for repo in cur_repos:
                if repo in RHEL_REPOS_MAP:
                    ppc_repos.append(RHEL_REPOS_MAP[repo])
                else:
                    ppc_repos.append(repo)

        else:
            ppc_repos = cur_repos

        content_set['ppc64le'] = ppc_repos

        if not os.path.exists(os.path.dirname(self._content_set_f)):
            os.makedirs(os.path.dirname(self._content_set_f))

        with open(self._content_set_f, 'w') as _file:
            yaml.dump(content_set, _file, default_flow_style=False)

        # check the cotnianter.yaml and pulp true
        return False

    def _prepate_odcs_container_yaml(self):
        container = {}

        if os.path.exists(self._container_f):
            with open(self._container_f, 'r') as _file:
                container = yaml.safe_load(_file)

        container['compose'] = {'pulp_repos': True}

        with open(self._container_f, 'w') as _file:
            yaml.dump(container, _file, default_flow_style=False)

    def _prepare_repository_rpm(self, repo):
        # no special handling is needed here, everything is in template
        pass
