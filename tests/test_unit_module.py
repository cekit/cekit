import os
import yaml

from cekit.config import Config
from cekit.descriptor import Module
from cekit.module import modules
from cekit.generator.base import Generator

module_desc = {
    'schema_version': 1,
    'name': 'master_mod',
    'modules': {
        'repositories': [{
            'name': 'module',
            'path': 'tests/modules/repo_1',
        },
        ]
    }
}


config = Config()
config.cfg['common'] = {'work_dir': '/tmp'}


def test_modules_repos(tmpdir):
    tmpdir = str(tmpdir.mkdir('target'))
    module = Module(module_desc, os.getcwd(), '/tmp')
    module.fetch_dependencies(tmpdir)
    assert 'foo' in [m['name'] for m in modules]

def test_issue_322(tmpdir):
    """tests a particular inheritance issue reported as GitHub issue #322"""
    target_dir = str(tmpdir.mkdir('target'))
    artifact_dir = str(tmpdir.mkdir('artifacts'))
    clone_dir = str(tmpdir.mkdir('clone'))

    descriptor = yaml.load(open("tests/issue_322/image.yaml").read())
    image = Module(descriptor=descriptor, path="tests/issue_322", artifact_dir=artifact_dir)
    image.fetch_dependencies(clone_dir)

    generator = Generator.__new__(Generator, descriptor_path="tests/issue_322", target=target_dir, builder="docker", overrides=None, params={})
    generator.image = image
    generator.target = target_dir
    generator.prepare_modules()
