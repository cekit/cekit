import mock
import os
import shutil
import unittest

from concreate.test.collector import TestCollector


class TestDockerfile(unittest.TestCase):

    def setUp(self):
        self.desc_dir = "/tmp/desc"
        self.target_dir = "/tmp/target_dir"
        shutil.rmtree(self.desc_dir, ignore_errors=True)
        shutil.rmtree(self.target_dir, ignore_errors=True)
        os.makedirs(self.desc_dir)
        os.makedirs(self.target_dir)

    @mock.patch.object(TestCollector, '_fetch_steps')
    @mock.patch.object(TestCollector, '_validate_steps_requirements')
    def test_collect_test_from_image_repo(self, m1, m2):
        collector = TestCollector(self.desc_dir, self.target_dir)

        feature_part = os.path.join('features', 'file.feature')

        features_file = os.path.join(self.desc_dir,
                                     'tests',
                                     feature_part)

        os.makedirs(os.path.dirname(features_file))
        open(features_file, 'w').close()

        self.assertTrue(collector.collect('v1'))
        collected_feature_file = os.path.join(self.target_dir,
                                              'test',
                                              feature_part)

        self.assertTrue(os.path.exists(collected_feature_file))

    @mock.patch.object(TestCollector, '_fetch_steps')
    @mock.patch.object(TestCollector, '_validate_steps_requirements')
    def test_collect_test_from_repository_root(self, m1, m2):
        collector = TestCollector(self.desc_dir, self.target_dir)
    
        features_file = os.path.join(self.target_dir,
                                     'repo',
                                     'foo',
                                     'tests',
                                     'features',
                                     'file.feature')

        os.makedirs(os.path.dirname(features_file))
        open(features_file, 'w').close()

        self.assertTrue(collector.collect('v1'))
        collected_feature_file = os.path.join(self.target_dir,
                                              'test',
                                              'features',
                                              'foo',
                                              'file.feature')

        self.assertTrue(os.path.exists(collected_feature_file))

    @mock.patch.object(TestCollector, '_fetch_steps')
    @mock.patch.object(TestCollector, '_validate_steps_requirements')
    def test_collect_test_from_module(self, m1, m2):
        collector = TestCollector(self.desc_dir, self.target_dir)
    
        features_file = os.path.join(self.target_dir,
                                     'image',
                                     'modules',
                                     'foo',
                                     'tests',
                                     'features',
                                     'file.feature')

        os.makedirs(os.path.dirname(features_file))
        open(features_file, 'w').close()

        self.assertTrue(collector.collect('v1'))
        collected_feature_file = os.path.join(self.target_dir,
                                              'test',
                                              'features',
                                              'foo',
                                              'file.feature')

        self.assertTrue(os.path.exists(collected_feature_file))

    @mock.patch.object(TestCollector, '_fetch_steps')
    @mock.patch.object(TestCollector, '_validate_steps_requirements')
    def test_collect_return_false(self, m1, m2):
        collector = TestCollector(self.desc_dir, self.target_dir)
        self.assertFalse(collector.collect('v1'))
