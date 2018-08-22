import os
import pytest
import re
import subprocess
import yaml

from cekit import tools
from cekit.generator.base import Generator
from cekit.descriptor import Module, Repository
from cekit.version import version as cekit_version

basic_config = {'release': 1,
                'version': 1,
                'from': 'scratch',
                'name': 'testimage'}

tools.cfg['common'] = {'redhat': True}

def print_test_name(value):
    if str(value).startswith('test'):
        return value
    return "\b"


odcs_fake_resp = """Result:
{u'arches': u'x86_64',
 u'flags': [],
 u'id': 2019,
 u'koji_event': None,
 u'koji_task_id': None,
 u'owner': u'dbecvari',
 u'packages': None,
 u'removed_by': None,
 u'result_repo': u'http://hidden/compose/Temporary',
 u'result_repofile': u'http://hidden/Temporary/odcs-2019.repo',
 u'results': [u'repository'],
 u'sigkeys': u'FD431D51',
 u'source': u'rhel-7-server-rpms',
 u'source_type': 4,
 u'state': 2,
 u'state_name': u'done',
 u'state_reason': u'Compose is generated successfully',
 u'time_done': u'2018-05-02T14:11:19Z',
 u'time_removed': None,
 u'time_submitted': u'2018-05-02T14:11:16Z',
 u'time_to_expire': u'2018-05-03T14:11:16Z'}"""


@pytest.mark.parametrize('name, desc_part, exp_regex', [
    ('test_run_user',
     {'run': {'user': 1347, 'cmd': ['whoami']}}, r'.*USER 1347\n+.*CMD.*'),
    ('test_default_run_user',
     {'run': {'cmd': ['whatever']}},  r'.*USER root\n+.*CMD.*'),
    ('test_custom_cmd',
     {'run': {'cmd': ['/usr/bin/date']}}, r'.*CMD \["/usr/bin/date"\]'),
    ('test_entrypoint',
     {'run': {'entrypoint': ['/usr/bin/date']}}, r'.*ENTRYPOINT \["/usr/bin/date"\]'),
    ('test_workdir',
     {'run': {'workdir': '/home/jboss'}}, r'.*WORKDIR /home/jboss'),
    ('test_volumes',
     {'volumes': [{'path': '/var/lib'},
                  {'path': '/usr/lib',
                   'name': 'path.lib'}]}, r'.*VOLUME \["/var/lib"\]\nVOLUME \["/usr/lib"\]'),
    ('test_ports',
     {'ports': [{'value': 8080},
                {'expose': False,
                 'value': 9999}]}, r'.*EXPOSE 8080$'),
    ('test_env', {'envs':  [{'name': 'CONFIG_ENV',
                             'example': 1234},
                            {'name': 'COMBINED_ENV',
                             'value': 'set_value',
                             'example': 'example_value',
                             'description': 'This is a description'}]},
     r' \\\s+COMBINED_ENV=\"set_value\" \\\s+JBOSS_IMAGE_NAME=\"testimage\" \\\s+JBOSS_IMAGE_VERSION=\"1\" \n'),
    ('test_execute',
     {'execute': [{'script': 'foo_script'}]},
     r'.*RUN [ "bash", "-x", "/tmp/scripts/testimage/foo_script" ].*'),
    ('test_execute_user',
     {'execute': [{'script': 'bar_script',
                   'user': 'bar_user'}]},
     r'.*USER bar_user\n+RUN [ "bash", "-x", "/tmp/scripts/testimage/foo_script" ].*'),
    ('test_concrt_label_version',
     {},
     r'.*org.concrt.version="%s".*' % cekit_version),
    ('test_cekit_label_version',
     {},
     r'.*io.cekit.version="%s".*' % cekit_version)],
                         ids=print_test_name)
def test_dockerfile_rendering(tmpdir, name, desc_part, exp_regex):

    target = str(tmpdir.mkdir('target'))

    generator = prepare_generator(target, desc_part)
    generator._params['redhat'] = True
    generator.render_dockerfile()

    regex_dockerfile(target, exp_regex)


@pytest.mark.parametrize('name, desc_part, exp_regex', [
    ('test_without_family',
     {}, r'JBOSS_IMAGE_NAME=\"testimage-tech-preview\"'),
    ('test_with_family',
        {'name': 'testimage/test'}, r'JBOSS_IMAGE_NAME=\"testimage-tech-preview/test\"')],
                         ids=print_test_name)
def test_dockerfile_rendering_tech_preview(tmpdir, name, desc_part, exp_regex):
    target = str(tmpdir.mkdir('target'))
    generator = prepare_generator(target, desc_part)
    generator._params = {'redhat': True}
    generator.generate_tech_preview()
    generator.render_dockerfile()
    regex_dockerfile(target, exp_regex)


def test_dockerfile_docker_odcs_pulp(tmpdir, mocker):
    mocker.patch.object(subprocess, 'check_output', return_value=odcs_fake_resp)
    mocker.patch.object(Repository, 'fetch')
    target = str(tmpdir.mkdir('target'))
    desc_part = {'packages': {'repositories': [{'name': 'foo',
                                                'odcs': {
                                                   'pulp': 'foo'
                                                }},
                                               ],
                              'install': ['a']}}

    generator = prepare_generator(target, desc_part, 'image')
    generator.prepare_repositories()
    generator.render_dockerfile()
    regex_dockerfile(target, 'repos/foo.repo')


def test_dockerfile_docker_odcs_rpm(tmpdir, mocker):
    mocker.patch.object(subprocess, 'check_output', return_value=odcs_fake_resp)
    mocker.patch.object(Repository, 'fetch')
    target = str(tmpdir.mkdir('target'))
    desc_part = {'packages': {'repositories': [{'name': 'foo',
                                                'rpm': 'foo-repo.rpm'}],
                              'install': ['a']}}

    generator = prepare_generator(target, desc_part, 'image')
    generator.prepare_repositories()
    generator.render_dockerfile()
    regex_dockerfile(target, 'RUN yum install -y foo-repo.rpm')


def test_dockerfile_osbs_odcs_pulp(tmpdir, mocker):
    mocker.patch.object(subprocess, 'check_output', return_value=odcs_fake_resp)
    mocker.patch.object(Repository, 'fetch')
    target = str(tmpdir.mkdir('target'))
    desc_part = {'packages': {'repositories': [{'name': 'foo',
                                                'odcs': {
                                                   'pulp': 'foo'
                                                }},
                                               ],
                              'install': ['a']}}

    generator = prepare_generator(target, desc_part, 'image', 'osbs')
    generator.prepare_repositories()
    with open(os.path.join(target, 'image', 'content_sets.yml'), 'r') as _file:
        content_sets = yaml.safe_load(_file)
        assert 'x86_64' in content_sets
        assert 'foo' in content_sets['x86_64']


def test_dockerfile_osbs_id_redhat(tmpdir, mocker):
    tools.cfg['common']['redhat'] = True
    mocker.patch.object(subprocess, 'check_output', return_value=odcs_fake_resp)
    mocker.patch.object(Repository, 'fetch')
    target = str(tmpdir.mkdir('target'))
    desc_part = {'packages': {'repositories': [{'name': 'foo',
                                                'id': 'foo'},
                                               ],
                              'install': ['a']}}

    generator = prepare_generator(target, desc_part, 'image', 'osbs')
    generator.prepare_repositories()
    with open(os.path.join(target, 'image', 'content_sets.yml'), 'r') as _file:
        content_sets = yaml.safe_load(_file)
        assert 'x86_64' in content_sets
        assert 'foo' in content_sets['x86_64']


def test_dockerfile_osbs_id_redhat_false(tmpdir, mocker):
    tools.cfg['common']['redhat'] = False
    mocker.patch.object(subprocess, 'check_output', return_value=odcs_fake_resp)
    mocker.patch.object(Repository, 'fetch')
    target = str(tmpdir.mkdir('target'))
    desc_part = {'packages': {'repositories': [{'name': 'foo',
                                                'id': 'foo'},
                                               ],
                              'install': ['a']}}

    generator = prepare_generator(target, desc_part, 'image', 'osbs')
    generator.prepare_repositories()
    assert not os.path.exists(os.path.join(target, 'image', 'content_sets.yml'))


def test_dockerfile_osbs_url_only(tmpdir, mocker):
    mocker.patch.object(subprocess, 'check_output', return_value=odcs_fake_resp)
    mocker.patch.object(Repository, 'fetch')
    target = str(tmpdir.mkdir('target'))
    desc_part = {'packages': {'repositories': [{'name': 'foo',
                                                'url': {
                                                   'repository': 'foo'
                                                }},
                                               ],
                              'install': ['a']}}

    generator = prepare_generator(target, desc_part, 'image', 'osbs')
    generator.prepare_repositories()
    assert not os.path.exists(os.path.join(target, 'image', 'content_sets.yml'))
    assert 'foo' in [x['url']['repository'] for x in generator.image['packages']['set_url']]


def test_dockerfile_osbs__and_url_(tmpdir, mocker):
    mocker.patch.object(subprocess, 'check_output', return_value=odcs_fake_resp)
    mocker.patch.object(Repository, 'fetch')
    target = str(tmpdir.mkdir('target'))
    desc_part = {'packages': {'repositories': [{'name': 'url',
                                                'url': {
                                                   'repository': 'foo'
                                                }},
                                               {'name': 'odcs',
                                                'odcs':{
                                                    'pulp': 'foo'
                                                }}
                                               ],
                              'install': ['a']}}

    generator = prepare_generator(target, desc_part, 'image', 'osbs')
    generator.prepare_repositories()

    assert 'set_url' not in generator.image['packages']
    assert 'foo' in [x['url']['repository'] for x in generator.image['packages']['repositories_injected']]
    with open(os.path.join(target, 'image', 'content_sets.yml'), 'r') as _file:
        content_sets = yaml.safe_load(_file)
        assert 'x86_64' in content_sets
        assert 'foo' in content_sets['x86_64']


def test_dockerfile_osbs_odcs_rpm(tmpdir, mocker):
    mocker.patch.object(subprocess, 'check_output', return_value=odcs_fake_resp)
    mocker.patch.object(Repository, 'fetch')
    target = str(tmpdir.mkdir('target'))
    desc_part = {'packages': {'repositories': [{'name': 'foo',
                                                'rpm': 'foo-repo.rpm'}],
                              'install': ['a']}}

    generator = prepare_generator(target, desc_part, 'image', 'osbs')
    generator.prepare_repositories()
    generator.render_dockerfile()
    regex_dockerfile(target, 'RUN yum install -y foo-repo.rpm')

    
def prepare_generator(target, desc_part, desc_type="image", engine="docker"):
    # create basic descriptor

    desc = basic_config.copy()
    desc.update(desc_part)

    image = Module(desc, '/tmp/', '/tmp')

    generator = Generator.__new__(Generator, image, target, engine, None, {})
    generator.image = image
    generator.target = target
    generator._type = 'docker'
    generator._wipe = False
    generator._params = {}
    generator._fetch_repos = False
    return generator


def regex_dockerfile(target, exp_regex):
    with open(os.path.join(target, 'image', 'Dockerfile'), "r") as fd:
        dockerfile_content = fd.read()
        regex = re.compile(exp_regex, re.MULTILINE)
        assert regex.search(dockerfile_content)
