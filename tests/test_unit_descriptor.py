import os
import tempfile
import unittest
import yaml

from concreate import descriptor
from concreate.errors import ConcreateError


class TestMergingDictionaries(unittest.TestCase):

    def test_merging_plain_dictionaries(self):
        dict1 = {'a': 1,
                 'b': 2}
        dict2 = {'b': 5,
                 'c': 3}
        expected = {'a': 1,
                    'b': 2,
                    'c': 3}
        self.assertEqual(expected,
                         descriptor.merge_dictionaries(dict1, dict2))

    def test_merging_emdedded_dictionaires(self):
        dict1 = {'a': 1,
                 'b': {'b1': 10,
                       'b2': 20}}
        dict2 = {'b': {'b2': 50,
                       'b3': 30},
                 'c': 3}
        expected = {'a': 1,
                    'b': {'b1': 10,
                          'b2': 20,
                          'b3': 30},
                    'c': 3}
        self.assertEqual(expected,
                         descriptor.merge_dictionaries(dict1, dict2))


class TestMergingLists(unittest.TestCase):

    def test_descriptor_schema_version(self):
        img_descriptor = descriptor.Descriptor.__new__(descriptor.Descriptor)
        img_descriptor.descriptor = {'schema_version': 1}
        img_descriptor.check_schema_version()

    def test_descriptor_schema_version_bad_version(self):
        img_descriptor = descriptor.Descriptor.__new__(descriptor.Descriptor)
        img_descriptor.descriptor = {'schema_version': 123}
        with self.assertRaises(ConcreateError):
            img_descriptor.check_schema_version()

    def test_merging_plain_lists(self):
        list1 = [1, 2, 3]
        list2 = [2, 3, 4, 5]
        expected = [1, 2, 3, 4, 5]
        self.assertEqual(descriptor.merge_lists(list1, list2),
                         expected)

    def test_merging_plain_list_oflist(self):
        list1 = [1, 2, 3]
        list2 = [3, 4, []]
        with self.assertRaises(ConcreateError):
            descriptor.merge_lists(list1, list2)

    def test_merging_list_of_dictionaries(self):
        list1 = [{'name': 1,
                  'a': 1,
                  'b': 2}, 'a']
        list2 = [{'name': 1,
                  'b': 3,
                  'c': 3},
                 {'name': 2,
                  'a': 123}]
        expected = [{'name': 1,
                     'a': 1,
                     'b': 2,
                     'c': 3},
                    'a',
                    {'name': 2,
                     'a': 123}]

        self.assertEqual(expected,
                         descriptor.merge_lists(list1, list2))


class TestLabels(unittest.TestCase):

    def setUp(self):
        _, self.descriptor = tempfile.mkstemp()

    def tearDown(self):
        os.remove(self.descriptor)

    def prepare_descriptor(self, data={}):
        image = {'name': 'image/name', 'version': 1.0,
                 'from': 'from/image', 'schema_version': 1}
        image.update(data)

        with open(self.descriptor, 'w') as outfile:
            yaml.dump(image, outfile, default_flow_style=False)

    def test_no_labels_should_be_added(self):
        self.prepare_descriptor()

        img_descriptor = descriptor.Descriptor(self.descriptor, 'image')
        img_descriptor._process_labels()

        self.assertIsNone(img_descriptor.label('description'))
        self.assertIsNone(img_descriptor.label('summary'))
        self.assertIsNone(img_descriptor.label('maintainer'))

    def test_description_label_should_be_added(self):
        self.prepare_descriptor({'description': 'This is image description'})

        img_descriptor = descriptor.Descriptor(self.descriptor, 'image')
        img_descriptor._process_labels()

        self.assertIsNone(img_descriptor.label('maintainer'))
        self.assertEqual(img_descriptor.label('description').get(
            'value'), 'This is image description')
        # In this case the 'summary' label should be also set
        self.assertEqual(img_descriptor.label('summary').get(
            'value'), 'This is image description')

    def test_description_and_summary_labels_should_not_be_overriden(self):
        self.prepare_descriptor({'description': 'This is image description', 'labels': [
                                {'name': 'summary', 'value': 'summary value'},
                                {'name': 'description', 'value': 'description value'}]})

        img_descriptor = descriptor.Descriptor(self.descriptor, 'image')
        img_descriptor._process_labels()

        self.assertIsNone(img_descriptor.label('maintainer'))
        self.assertEqual(img_descriptor.label(
            'description').get('value'), 'description value')
        self.assertEqual(img_descriptor.label(
            'summary').get('value'), 'summary value')
