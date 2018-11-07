import os
import yaml
import shutil

from cekit.config import Config
from cekit.descriptor import Module
from cekit.module import modules
from cekit.generator.base import Generator

module_desc = {
    'schema_version': 1,
    'name': 'master_mod',
    'version': '1.0',
    'modules': {
        'repositories': [{
            'name': 'module',
            'path': 'modules/repo_1',
        },
        ]
    }
}


config = Config()
config.cfg['common'] = {'work_dir': '/tmp'}


def test_modules_repos(tmpdir):
    target_dir = str(tmpdir.mkdir('target'))
    image_yaml = os.path.join(os.path.dirname(target_dir), "image.yaml")
    with open(image_yaml, 'w') as outfile:
        yaml.dump(module_desc, outfile, default_flow_style=False)

    shutil.copytree(os.path.join(os.path.dirname(__file__), "modules"), os.path.join(os.path.dirname(target_dir), "modules"))

    generator = Generator(descriptor_path=image_yaml, target=target_dir, builder="docker", overrides=None, params={})
    generator.init()

    assert generator._module_registry.get_module('foo') != None

def test_issue_322(tmpdir):
    """tests a particular inheritance issue reported as GitHub issue #322"""
    test_dir = os.path.join(str(tmpdir), "issue_322")
    shutil.copytree(os.path.join(os.path.dirname(__file__), "issue_322"), test_dir)

    target_dir = os.path.join(test_dir, 'target')
    image_yaml = os.path.join(test_dir, "image.yaml")

    generator = Generator(descriptor_path=image_yaml, target=target_dir, builder="docker", overrides=None, params={})
    generator.init()
