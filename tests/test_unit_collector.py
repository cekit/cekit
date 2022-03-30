import os
import shutil

import pytest

from cekit.test.collector import BehaveTestCollector

desc_dir = "/tmp/desc"
target_dir = "/tmp/target_dir"

steps_url = "https://github.com/cekit/behave-test-steps"


@pytest.fixture
def prepare_dirs():
    shutil.rmtree(desc_dir, ignore_errors=True)
    shutil.rmtree(target_dir, ignore_errors=True)
    os.makedirs(desc_dir)
    os.makedirs(target_dir)


def test_collect_test_from_image_repo(prepare_dirs, mocker):
    mocker.patch.object(BehaveTestCollector, "_fetch_steps")
    collector = BehaveTestCollector(desc_dir, target_dir)

    features_file = os.path.join(desc_dir, "tests", "features", "file.feature")

    os.makedirs(os.path.dirname(features_file))
    open(features_file, "w").close()

    assert collector.collect("1", steps_url)
    collected_feature_file = os.path.join(
        target_dir, "test", "features", "image", "file.feature"
    )

    assert os.path.exists(collected_feature_file)


def test_collect_test_from_repository_root(prepare_dirs, mocker):
    mocker.patch.object(BehaveTestCollector, "_fetch_steps")
    collector = BehaveTestCollector(desc_dir, target_dir)

    features_file = os.path.join(
        target_dir, "repo", "foo", "tests", "features", "file.feature"
    )

    os.makedirs(os.path.dirname(features_file))
    open(features_file, "w").close()

    assert collector.collect("1", steps_url)
    collected_feature_file = os.path.join(
        target_dir, "test", "features", "foo", "file.feature"
    )

    assert os.path.exists(collected_feature_file)


def test_collect_test_from_module(prepare_dirs, mocker):
    mocker.patch.object(BehaveTestCollector, "_fetch_steps")
    collector = BehaveTestCollector(desc_dir, target_dir)

    features_file = os.path.join(
        target_dir, "image", "modules", "foo", "tests", "features", "file.feature"
    )

    os.makedirs(os.path.dirname(features_file))
    open(features_file, "w").close()

    assert collector.collect("1", steps_url)
    collected_feature_file = os.path.join(
        target_dir, "test", "features", "foo", "file.feature"
    )

    assert os.path.exists(collected_feature_file)


def test_collect_return_false(prepare_dirs, mocker):
    mocker.patch.object(BehaveTestCollector, "_fetch_steps")

    collector = BehaveTestCollector(desc_dir, target_dir)

    assert not collector.collect("1", steps_url)
