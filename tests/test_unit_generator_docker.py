# -*- encoding: utf-8 -*-

# pylint: disable=protected-access

import os

from contextlib import contextmanager

import pytest
import yaml

from cekit.config import Config
from cekit.errors import CekitError
from cekit.generator.docker import DockerGenerator
from cekit.descriptor import Image


odcs_fake_resp = b"""Result:
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

odcs_fake_invalid_resp = b"""Result:
{u'arches': u'x86_64',
 u'results': [u'repository'],
 u'sigkeys': u'FD431D51',
 u'source': u'rhel-7-server-rpms',
 u'source_type': 4,
 u'state': 1,
 u'state_name': u'fail',
 u'state_reason': u'Compose failed',
 u'time_to_expire': u'2018-05-03T14:11:16Z'}"""


@contextmanager
def cekit_config(redhat=False):
    config = Config()
    config.cfg.update({'common': {'redhat': redhat}})

    try:
        yield config
    finally:
        pass


@contextmanager
def docker_generator(tmpdir, overrides=None):
    if overrides is None:
        overrides = {}

    image_dir = str(tmpdir)
    target_dir = os.path.join(image_dir, 'target')
    yield DockerGenerator(image_dir, target_dir, overrides)


def setup_function():
    # For each invocation, reset the config
    Config.cfg = {'common': {}}


def test_prepare_content_sets_should_not_fail_when_cs_is_none(tmpdir):
    with docker_generator(tmpdir) as generator:
        with cekit_config(redhat=True):
            assert generator._prepare_content_sets(None) is False


def test_prepare_content_sets_should_not_fail_when_cs_is_empty(tmpdir):
    with docker_generator(tmpdir) as generator:
        with cekit_config(redhat=True):
            assert generator._prepare_content_sets({}) is False


def test_large_labels_should_break_lines(tmpdir):
    image = Image(yaml.safe_load("""
    from: foo
    name: test/foo
    version: 1.9
    labels:
      - name: 'the.large.label'
        value: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec pretium finibus lorem vitae pellentesque. Maecenas tincidunt amet.
    """), 'foo')
    with docker_generator(tmpdir) as generator:
        generator.image = image
        with cekit_config(redhat=True):
            generator.add_build_labels()
            assert image.labels[0].value == "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec pretium finibus lorem vitae pellentesque. Maecenas tincidunt amet\\\n.\\\n"


def test_prepare_content_sets_should_fail_when_cs_are_note_defined_for_current_platform(tmpdir, mocker):
    mocker.patch('cekit.generator.base.platform.machine',
                 return_value="current_platform")

    with docker_generator(tmpdir) as generator:
        with cekit_config(redhat=True):
            with pytest.raises(CekitError, match="There are no content_sets defined for platform 'current_platform'!"):
                assert generator._prepare_content_sets(
                    {'invalid_platform': ['ca1', 'cs2']}) is False


def test_prepare_content_sets_should_request_odcs(tmpdir, mocker):
    mocker.patch('cekit.generator.base.platform.machine',
                 return_value="current_platform")
    mock_odcs = mocker.patch(
        'cekit.generator.base.subprocess.check_output', return_value=odcs_fake_resp)

    with docker_generator(tmpdir) as generator:
        generator.image = {'osbs': {'configuration': {'container': {'compose': {}}}}}

        with cekit_config(redhat=True):
            assert generator._prepare_content_sets(
                {'current_platform': ['ca1', 'cs2']}) == "http://hidden/Temporary/odcs-2019.repo"

    mock_odcs.assert_called_once_with(['/usr/bin/odcs', '--redhat', 'create', 'pulp', 'ca1 cs2'])


def test_prepare_content_sets_should_request_odcs_with_hidden_repos_flag(tmpdir, mocker):
    mocker.patch('cekit.generator.base.platform.machine',
                 return_value="current_platform")
    mock_odcs = mocker.patch(
        'cekit.generator.base.subprocess.check_output', return_value=odcs_fake_resp)

    with docker_generator(tmpdir) as generator:
        generator.image = {'osbs': {'configuration': {'container': {
            'compose': {'include_unpublished_pulp_repos': True}}}}}

        with cekit_config(redhat=True):
            assert generator._prepare_content_sets(
                {'current_platform': ['ca1', 'cs2']}) == "http://hidden/Temporary/odcs-2019.repo"

    mock_odcs.assert_called_once_with(
        ['/usr/bin/odcs', '--redhat', 'create', '--flag', 'include_unpublished_pulp_repos', 'pulp', 'ca1 cs2'])


def test_prepare_content_sets_should_handle_incorrect_state(tmpdir, mocker):
    mocker.patch('cekit.generator.base.platform.machine',
                 return_value="current_platform")
    mock_odcs = mocker.patch(
        'cekit.generator.base.subprocess.check_output', return_value=odcs_fake_invalid_resp)

    with docker_generator(tmpdir) as generator:
        generator.image = {'osbs': {'configuration': {'container': {
            'compose': {}}}}}

        with cekit_config(redhat=True):
            with pytest.raises(CekitError, match="Cannot create content set: 'Compose failed'"):
                generator._prepare_content_sets({'current_platform': ['ca1', 'cs2']})

    mock_odcs.assert_called_once_with(
        ['/usr/bin/odcs', '--redhat', 'create', 'pulp', 'ca1 cs2'])


def test_prepare_content_sets_should_handle_no_odcs_command(tmpdir, mocker):
    mocker.patch('cekit.generator.base.platform.machine',
                 return_value="current_platform")
    mock_odcs = mocker.patch(
        'cekit.generator.base.subprocess.check_output', side_effect=OSError)

    with docker_generator(tmpdir) as generator:
        generator.image = {'osbs': {'configuration': {'container': {
            'compose': {}}}}}

        with cekit_config(redhat=True):
            with pytest.raises(CekitError, match="ODCS is not installed, please install 'odcs-client' package"):
                generator._prepare_content_sets({'current_platform': ['ca1', 'cs2']})

    mock_odcs.assert_called_once_with(
        ['/usr/bin/odcs', '--redhat', 'create', 'pulp', 'ca1 cs2'])
