from concreate.descriptor import Module
from concreate.module import modules

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


def test_modules_repos(tmpdir):
    tmpdir = str(tmpdir.mkdir('target'))
    module = Module(module_desc, tmpdir)
    module.fetch_dependencies(tmpdir)
    assert 'foo' in [m['name'] for m in modules]
