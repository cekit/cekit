from cekit.tools import Map
from cekit.errors import CekitError
from cekit.descriptor import Image
import glob
import logging
import os
import pytest
import subprocess
import time
import yaml

try:
    from unittest.mock import call
except ImportError:
    from mock import call

from cekit.builders.docker_builder import DockerBuilder
from cekit.builder import Builder
from cekit.config import Config


config = Config()


@pytest.fixture(autouse=True)
def reset_config():
    config.cfg['common'] = {}


config = Config()
config.cfg['common'] = {'redhat': True}


def test_osbs_builder_defaults(mocker):
    mocker.patch.object(subprocess, 'check_output')

    builder = create_builder_object(mocker, 'osbs', {})

    assert builder._fedpkg == '/usr/bin/fedpkg'
    assert builder._koji == '/usr/bin/koji'
    assert builder._koji_url == 'https://koji.fedoraproject.org/koji'


def test_osbs_builder_redhat(mocker):
    config.cfg['common'] = {'redhat': True}
    mocker.patch.object(subprocess, 'check_output')

    builder = create_builder_object(mocker, 'osbs', {})

    assert builder._fedpkg == '/usr/bin/rhpkg'
    assert builder._koji == '/usr/bin/brew'
    assert builder._koji_url == 'https://brewweb.engineering.redhat.com/brew'


def test_osbs_builder_use_rhpkg_stage(mocker):
    config.cfg['common'] = {'redhat': True}
    mocker.patch.object(subprocess, 'check_output')

    builder = create_builder_object(mocker, 'osbs', {'stage': True})

    assert builder._fedpkg == '/usr/bin/rhpkg-stage'
    assert builder._koji == '/usr/bin/brew-stage'
    assert builder._koji_url == 'https://brewweb.stage.engineering.redhat.com/brew'


def test_osbs_builder_custom_commit_msg(mocker):
    mocker.patch.object(subprocess, 'check_output')

    builder = create_builder_object(mocker, 'osbs', {'stage': True,
                                                     'commit_message': 'foo'})

    assert builder.params.commit_message == 'foo'


def test_osbs_builder_nowait(mocker):
    mocker.patch.object(subprocess, 'check_output')

    builder = create_builder_object(mocker, 'osbs', {'nowait': True})

    assert builder.params.nowait is True


def test_osbs_builder_user(mocker):
    mocker.patch.object(subprocess, 'check_output')

    builder = create_builder_object(mocker, 'osbs', {'user': 'UserFoo'})
    assert builder.params.user == 'UserFoo'


def test_merge_container_yaml_no_limit_arch(mocker, tmpdir):
    mocker.patch.object(glob, 'glob', return_value=False)
    mocker.patch.object(subprocess, 'check_output')

    builder = create_builder_object(mocker, 'osbs', {})
    builder.dist_git_dir = str(tmpdir.mkdir('target'))

    container_yaml_f = 'container.yaml'

    source = 'souce_cont.yaml'
    with open(source, 'w') as file_:
        yaml.dump({'tags': ['foo']}, file_)

    builder._merge_container_yaml(source, container_yaml_f)

    with open(container_yaml_f, 'r') as file_:
        container_yaml = yaml.safe_load(file_)
    os.remove(container_yaml_f)
    os.remove(source)

    assert 'paltforms' not in container_yaml


def test_merge_container_yaml_limit_arch(mocker, tmpdir):
    mocker.patch.object(glob, 'glob', return_value=True)
    mocker.patch.object(subprocess, 'check_output')
    builder = create_builder_object(mocker, 'osbs', {})
    builder.dist_git_dir = str(tmpdir.mkdir('target'))

    container_yaml_f = 'container.yaml'

    source = 'souce_cont.yaml'
    with open(source, 'w') as file_:
        yaml.dump({'tags': ['foo']}, file_)

    builder._merge_container_yaml(source, container_yaml_f)

    with open(container_yaml_f, 'r') as file_:
        container_yaml = yaml.safe_load(file_)
    os.remove(container_yaml_f)
    os.remove(source)

    assert 'x86_64' in container_yaml['platforms']['only']
    assert len(container_yaml['platforms']['only']) == 1


class DistGitMock(object):
    def add(self):
        pass

    def stage_modified(self):
        pass

    @staticmethod
    def repo_info(path):
        pass

    def prepare(self, stage, user=None):
        pass

    def clean(self):
        pass


def create_builder_object(mocker, builder, params, common_params={'target': 'something'}):
    if 'docker' == builder:
        from cekit.builders.docker_builder import DockerBuilder as BuilderImpl
    elif 'osbs' == builder:
        from cekit.builders.osbs import OSBSBuilder as BuilderImpl
    elif 'buildah' == builder:
        from cekit.builders.buildah import BuildahBuilder as BuilderImpl
    else:
        raise Exception("Builder engine %s is not supported" % builder)

    mocker.patch('cekit.tools.decision')

    builder = BuilderImpl(Map(common_params), Map(params))
    builder.dist_git_dir = '/tmp'
    builder.dist_git = DistGitMock()
    builder.artifacts = []
    return builder


def test_osbs_builder_run_brew_stage(mocker):
    config.cfg['common'] = {'redhat': True}
    params = {'stage': True}

    check_output = mocker.patch.object(subprocess, 'check_output', autospec=True, side_effect=[
                                       b'ssh://user:password@something.redhat.com/containers/openjdk', b'c5a0731b558c8a247dd7f85b5f54462cd5b68b23', b'12345'])
    builder = create_builder_object(mocker, 'osbs', params)
    mocker.patch.object(builder, '_wait_for_osbs_task')
    builder.dist_git.branch = "some-branch"
    builder.run()

    check_output.assert_has_calls([
        call(['git', 'remote', 'get-url', 'origin']),
        call(['git', 'rev-parse', 'HEAD']),
        call(['/usr/bin/brew-stage', 'call', '--python', 'buildContainer', '--kwargs',
              "{'src': 'git://something.redhat.com/containers/openjdk#c5a0731b558c8a247dd7f85b5f54462cd5b68b23', 'target': 'some-branch-containers-candidate', 'opts': {'scratch': True, 'git_branch': 'some-branch', 'yum_repourls': []}}"])
    ])

    builder._wait_for_osbs_task.assert_called_once_with('12345')


def test_osbs_builder_run_brew(mocker):
    config.cfg['common'] = {'redhat': True}

    check_output = mocker.patch.object(subprocess, 'check_output', autospec=True, side_effect=[
                                       b'ssh://user:password@something.redhat.com/containers/openjdk', b'c5a0731b558c8a247dd7f85b5f54462cd5b68b23', b'12345'])
    builder = create_builder_object(mocker, 'osbs', {})
    mocker.patch.object(builder, '_wait_for_osbs_task')
    builder.dist_git.branch = "some-branch"
    builder.run()

    check_output.assert_has_calls([
        call(['git', 'remote', 'get-url', 'origin']),
        call(['git', 'rev-parse', 'HEAD']),
        call(['/usr/bin/brew', 'call', '--python', 'buildContainer', '--kwargs',
              "{'src': 'git://something.redhat.com/containers/openjdk#c5a0731b558c8a247dd7f85b5f54462cd5b68b23', 'target': 'some-branch-containers-candidate', 'opts': {'scratch': True, 'git_branch': 'some-branch', 'yum_repourls': []}}"])
    ])

    builder._wait_for_osbs_task.assert_called_once_with('12345')


def test_osbs_builder_run_koji(mocker):
    check_output = mocker.patch.object(subprocess, 'check_output', autospec=True, side_effect=[
                                       b'ssh://user:password@something.redhat.com/containers/openjdk', b'c5a0731b558c8a247dd7f85b5f54462cd5b68b23', b'12345'])
    builder = create_builder_object(mocker, 'osbs', {}, {'redhat': False, 'target': 'something'})
    mocker.patch.object(builder, '_wait_for_osbs_task')
    builder.dist_git.branch = "some-branch"
    builder.run()

    check_output.assert_has_calls([
        call(['git', 'remote', 'get-url', 'origin']),
        call(['git', 'rev-parse', 'HEAD']),
        call(['/usr/bin/koji', 'call', '--python', 'buildContainer', '--kwargs',
              "{'src': 'git://something.redhat.com/containers/openjdk#c5a0731b558c8a247dd7f85b5f54462cd5b68b23', 'target': 'some-branch-containers-candidate', 'opts': {'scratch': True, 'git_branch': 'some-branch', 'yum_repourls': []}}"])
    ])

    builder._wait_for_osbs_task.assert_called_once_with('12345')


def test_osbs_builder_run_brew_nowait(mocker):
    params = {'nowait': True}

    check_output = mocker.patch.object(subprocess, 'check_output', autospec=True, side_effect=[
                                       b'ssh://user:password@something.redhat.com/containers/openjdk', b'c5a0731b558c8a247dd7f85b5f54462cd5b68b23', b'12345'])
    builder = create_builder_object(mocker, 'osbs', params)
    mocker.patch.object(builder, '_wait_for_osbs_task')
    builder.dist_git.branch = "some-branch"
    builder.run()

    builder._wait_for_osbs_task.assert_not_called()


def test_osbs_builder_run_brew_user(mocker):
    config.cfg['common'] = {'redhat': True}
    params = {'user': 'Foo'}

    check_output = mocker.patch.object(subprocess, 'check_output', autospec=True, side_effect=[
                                       b'ssh://user:password@something.redhat.com/containers/openjdk', b'c5a0731b558c8a247dd7f85b5f54462cd5b68b23', b'12345'])
    builder = create_builder_object(mocker, 'osbs', params)
    mocker.patch.object(builder, '_wait_for_osbs_task')
    builder.dist_git.branch = "some-branch"
    builder.run()

    check_output.assert_called_with(['/usr/bin/brew', '--user', 'Foo', 'call', '--python', 'buildContainer', '--kwargs',
                                     "{'src': 'git://something.redhat.com/containers/openjdk#c5a0731b558c8a247dd7f85b5f54462cd5b68b23', 'target': 'some-branch-containers-candidate', 'opts': {'scratch': True, 'git_branch': 'some-branch', 'yum_repourls': []}}"])


def test_osbs_builder_run_brew_target(mocker):
    config.cfg['common'] = {'redhat': True}
    params = {'koji_target': 'Foo'}

    check_output = mocker.patch.object(subprocess, 'check_output', autospec=True, side_effect=[
                                       b'ssh://user:password@something.redhat.com/containers/openjdk', b'c5a0731b558c8a247dd7f85b5f54462cd5b68b23', b'12345'])
    builder = create_builder_object(mocker, 'osbs', params)
    mocker.patch.object(builder, '_wait_for_osbs_task')
    builder.dist_git.branch = "some-branch"
    builder.run()

    check_output.assert_called_with(['/usr/bin/brew', 'call', '--python', 'buildContainer', '--kwargs',
                                     "{'src': 'git://something.redhat.com/containers/openjdk#c5a0731b558c8a247dd7f85b5f54462cd5b68b23', 'target': 'Foo', 'opts': {'scratch': True, 'git_branch': 'some-branch', 'yum_repourls': []}}"])


def test_osbs_wait_for_osbs_task_finished_successfully(mocker):
    config.cfg['common'] = {'redhat': True}
    builder = create_builder_object(mocker, 'osbs', {})

    sleep = mocker.patch.object(time, 'sleep')
    check_output = mocker.patch.object(subprocess, 'check_output', side_effect=[
        b'''{
            "state": 2,
            "create_time": "2019-02-15 13:14:58.278557",
            "create_ts": 1550236498.27856,
            "owner": 2485,
            "host_id": 283,
            "method": "buildContainer",
            "completion_ts": 1550237431.0166,
            "arch": "noarch",
            "id": 20222655
        }'''])

    assert builder._wait_for_osbs_task('12345') == True

    check_output.assert_called_with(
        ['/usr/bin/brew', 'call', '--json-output', 'getTaskInfo', '12345'])
    sleep.assert_not_called()


def test_osbs_wait_for_osbs_task_in_progress(mocker):
    config.cfg['common'] = {'redhat': True}
    builder = create_builder_object(mocker, 'osbs', {})

    sleep = mocker.patch.object(time, 'sleep')
    check_output = mocker.patch.object(subprocess, 'check_output', side_effect=[
        b'''{
            "state": 1,
            "create_time": "2019-02-15 13:14:58.278557",
            "create_ts": 1550236498.27856,
            "owner": 2485,
            "host_id": 283,
            "method": "buildContainer",
            "completion_ts": 1550237431.0166,
            "arch": "noarch",
            "id": 20222655
        }''', b'''{
            "state": 2,
            "create_time": "2019-02-15 13:14:58.278557",
            "create_ts": 1550236498.27856,
            "owner": 2485,
            "host_id": 283,
            "method": "buildContainer",
            "completion_ts": 1550237431.0166,
            "arch": "noarch",
            "id": 20222655
        }'''])

    assert builder._wait_for_osbs_task('12345') == True

    check_output.assert_has_calls([
        call(['/usr/bin/brew', 'call', '--json-output', 'getTaskInfo', '12345']),
        call(['/usr/bin/brew', 'call', '--json-output', 'getTaskInfo', '12345'])
    ])
    sleep.assert_called_once_with(20)


def test_osbs_wait_for_osbs_task_failed(mocker):
    config.cfg['common'] = {'redhat': True}
    builder = create_builder_object(mocker, 'osbs', {})

    sleep = mocker.patch.object(time, 'sleep')
    check_output = mocker.patch.object(subprocess, 'check_output', side_effect=[
        b'''{
            "state": 5,
            "create_time": "2019-02-15 13:14:58.278557",
            "create_ts": 1550236498.27856,
            "owner": 2485,
            "host_id": 283,
            "method": "buildContainer",
            "completion_ts": 1550237431.0166,
            "arch": "noarch",
            "id": 20222655
        }'''])

    with pytest.raises(CekitError, match="Task 12345 did not finish successfully, please check the task logs!"):
        builder._wait_for_osbs_task('12345')

    check_output.assert_called_with(
        ['/usr/bin/brew', 'call', '--json-output', 'getTaskInfo', '12345'])
    sleep.assert_not_called()


@pytest.mark.parametrize('artifact,src,target', [
    (
        {
            'path': 'some-path.jar',
            'md5': 'aaabbb'
        },
        'image/some-path.jar',
        'osbs/repo/some-path.jar'
    ),
    (
        {
            'name': 'some-name',
            'path': 'some-path.jar',
            'md5': 'aaabbb'
        },
        'image/some-name',
        'osbs/repo/some-name'
    ),
    (
        {
            'target': 'some-target.jar',
            'path': 'some-path.jar',
            'md5': 'aaabbb'
        },
        'image/some-target.jar',
        'osbs/repo/some-target.jar'
    ),
    (
        {
            'name': 'some-name',
            'md5': 'aaabbb'
        },
        'image/some-name',
        'osbs/repo/some-name'
    ),
    (
        {
            'name': 'some-name',
            'target': 'some-target.jar',
            'md5': 'aaabbb'
        },
        'image/some-target.jar',
        'osbs/repo/some-target.jar'
    )
])
def test_osbs_copy_artifacts_to_dist_git(mocker, tmpdir, artifact, src, target):
    os.makedirs(os.path.join(str(tmpdir), 'image'))

    copy_mock = mocker.patch('cekit.builders.osbs.shutil.copy')

    dist_git_class = mocker.patch('cekit.builders.osbs.DistGit')
    dist_git_class.return_value = DistGitMock()

    config.cfg['common'] = {'redhat': True, 'work_dir': str(tmpdir)}

    image_descriptor = {
        'schema_version': 1,
        'from': 'centos:latest',
        'name': 'test/image',
        'version': '1.0',
        'labels': [{'name': 'foo', 'value': 'bar'}, {'name': 'labela', 'value': 'a'}],
        'osbs': {
            'repository': {
                'name': 'repo',
                'branch': 'branch'
            }
        },
        'artifacts': [
            artifact
        ]
    }

    image = Image(image_descriptor, os.path.dirname(os.path.abspath(str(tmpdir))))

    # TODO Rewrite this
    # This is only to mark that the plain artifact was not available in koji
    # So we need to add it to lookaside cache. This does not hurt non-plain artifacts, so we
    # can add it for all artifacts
    image.artifacts[0]['lookaside'] = True

    builder = create_osbs_build_object(mocker, 'osbs')
    builder.target = str(tmpdir)
    builder.prepare(image)
    dist_git_class.assert_called_once_with(os.path.join(
        str(tmpdir), 'osbs', 'repo'), str(tmpdir), 'repo', 'branch')

    calls = [mocker.call('Dockerfile', os.path.join(str(tmpdir), 'osbs/repo/Dockerfile')),
             mocker.call(os.path.join(str(tmpdir), src), os.path.join(str(tmpdir), target))]

    copy_mock.assert_has_calls(calls)


def test_docker_builder_defaults():
    params = {'tags': ['foo', 'bar']}
    builder = Builder('docker', 'tmp', params)

    assert builder._tags == ['foo', 'bar']
    assert builder._no_squash == False


def test_docker_squashing_enabled(mocker):
    builder = DockerBuilder(Map({'target': 'something'}), Map({'tags': ['foo', 'bar']}))

    # None is fine here, default values for params are tested in different place
    assert builder.params.no_squash == None

    docker_client_class = mocker.patch('cekit.builders.docker_builder.APIClientClass')
    docker_client = docker_client_class.return_value
    mocker.patch.object(builder, '_build_with_docker')
    mocker.patch.object(builder, '_squash')
    builder._build_with_docker.return_value = "1654234sdf56"

    builder.run()

    builder._build_with_docker.assert_called_once_with(docker_client)
    builder._squash.assert_called_once_with(docker_client, "1654234sdf56")


def test_docker_squashing_disabled(mocker):
    builder = DockerBuilder(Map({'target': 'something'}), Map(
        {'no_squash': True, 'tags': ['foo', 'bar']}))

    assert builder.params.no_squash == True

    docker_client_class = mocker.patch('cekit.builders.docker_builder.APIClientClass')
    docker_client = docker_client_class.return_value
    mocker.patch.object(builder, '_build_with_docker')
    mocker.patch.object(builder, '_squash')

    builder._build_with_docker.return_value = "1654234sdf56"

    builder.run()

    builder._build_with_docker.assert_called_once_with(docker_client)
    builder._squash.assert_not_called()


def test_docker_squashing_parameters(mocker):
    builder = DockerBuilder(Map({'target': 'something'}), Map({'tags': ['foo', 'bar']}))

    # None is fine here, default values for params are tested in different place
    assert builder.params.no_squash == None

    docker_client_class = mocker.patch('cekit.builders.docker_builder.APIClientClass')
    squash_class = mocker.patch('cekit.builders.docker_builder.Squash')
    squash = squash_class.return_value
    docker_client = docker_client_class.return_value
    mocker.patch.object(builder, '_build_with_docker', return_value="1654234sdf56")

    builder.generator = Map({'image': {'from': 'FROM'}})

    builder.run()

    squash_class.assert_called_once_with(
        cleanup=True, docker=docker_client, from_layer="FROM", image="1654234sdf56", log=logging.getLogger('cekit'))
    squash.run.assert_called_once_with()
    builder._build_with_docker.assert_called_once_with(docker_client)


def test_buildah_builder_run(mocker):
    params = {'tags': ['foo', 'bar']}
    check_call = mocker.patch.object(subprocess, 'check_call')
    builder = create_builder_object(mocker, 'buildah', params)
    builder.run()

    check_call.assert_called_once_with([
        '/usr/bin/buildah',
        'build-using-dockerfile',
        '-t', 'foo',
        '-t', 'bar',
        'something/image'])


def test_buildah_builder_run_pull(mocker):
    params = {'tags': ['foo', 'bar'], 'pull': True}
    check_call = mocker.patch.object(subprocess, 'check_call')
    builder = create_builder_object(mocker, 'buildah', params)
    builder.run()

    check_call.assert_called_once_with([
        '/usr/bin/buildah',
        'build-using-dockerfile',
        '--pull-always',
        '-t', 'foo',
        '-t', 'bar',
        'something/image'])
