import os
import tempfile
import unittest
import yaml

from concreate import descriptor
from concreate.errors import ConcreateError


class TestDescriptor(unittest.TestCase):

    def test_descriptor_schema_version(self):
        img_descriptor = descriptor.Descriptor.__new__(descriptor.Descriptor)
        img_descriptor.descriptor = {'schema_version': 1}
        img_descriptor.check_schema_version()

    def test_descriptor_schema_version_bad_version(self):
        img_descriptor = descriptor.Descriptor.__new__(descriptor.Descriptor)
        img_descriptor.descriptor = {'schema_version': 123}
        with self.assertRaises(ConcreateError):
            img_descriptor.check_schema_version()


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
