import pytest
import yaml

from concreate import descriptor
from concreate.errors import ConcreateError


def test_descriptor_schema_version():
    img_descriptor = descriptor.Descriptor.__new__(descriptor.Descriptor)
    img_descriptor.descriptor = {'schema_version': 1}
    img_descriptor.check_schema_version()


def test_descriptor_schema_version_bad_version():
    img_descriptor = descriptor.Descriptor.__new__(descriptor.Descriptor)
    img_descriptor.descriptor = {'schema_version': 123}
    with pytest.raises(ConcreateError):
        img_descriptor.check_schema_version()


def prepare_descriptor(path, data={}):
    image = {'name': 'image/name', 'version': 1.0,
             'from': 'from/image', 'schema_version': 1}
    image.update(data)

    with open(path, 'w') as fd:
        yaml.dump(image, fd, default_flow_style=False)
    return path


def test_no_labels_should_be_added(tmpdir):
    descriptor_path = prepare_descriptor(str(tmpdir.mkdir('image').join('image.yaml')))

    img_descriptor = descriptor.Descriptor(descriptor_path, 'image')
    img_descriptor._process_labels()

    assert img_descriptor.label('description') is None
    assert img_descriptor.label('summary') is None
    assert img_descriptor.label('maintainer') is None


def test_description_label_should_be_added(tmpdir):
    descriptor_path = prepare_descriptor(str(tmpdir.mkdir('image').join('image.yaml')),
                                         {'description': 'This is image description'})

    img_descriptor = descriptor.Descriptor(descriptor_path, 'image')
    img_descriptor._process_labels()

    assert img_descriptor.label('maintainer') is None
    assert img_descriptor.label('description').get('value') == 'This is image description'
    # In this case the 'summary' label should be also set
    assert img_descriptor.label('summary').get('value') == 'This is image description'


def test_description_and_summary_labels_should_not_be_overriden(tmpdir):
    descriptor_path = prepare_descriptor(str(tmpdir.mkdir('image').join('image.yaml')),
                                         {'description': 'This is image description', 'labels': [
                                             {'name': 'summary',
                                              'value': 'summary value'},
                                             {'name': 'description',
                                              'value': 'description value'}]})

    img_descriptor = descriptor.Descriptor(descriptor_path, 'image')
    img_descriptor._process_labels()

    assert img_descriptor.label('maintainer') is None
    assert img_descriptor.label('description').get('value') == 'description value'
    assert img_descriptor.label('summary').get('value') == 'summary value'


def test_override_default_user_run(tmpdir):
    descriptor_path = prepare_descriptor(str(tmpdir.mkdir('image').join('image.yaml')))
    overrides_path = prepare_descriptor(str(tmpdir.mkdir('override').join('overrides.yaml')),
                                        {'run': {'user': 123}})

    img_descriptor = descriptor.Descriptor(descriptor_path, 'image')
    overrides_descriptor = descriptor.Descriptor(overrides_path, 'image')
    overrides_descriptor.merge(img_descriptor)
    overrides_descriptor.prepare_defaults()

    assert overrides_descriptor.descriptor['run']['user'] == 123


def test_override_default_user_kept(tmpdir):
    descriptor_path = prepare_descriptor(str(tmpdir.mkdir('image').join('image.yaml')),
                                         {'run': {'user': 123}})
    overrides_path = prepare_descriptor(str(tmpdir.mkdir('override').join('overrides.yaml')))

    img_descriptor = descriptor.Descriptor(descriptor_path, 'image')
    overrides_descriptor = descriptor.Descriptor(overrides_path, 'image')
    overrides_descriptor.merge(img_descriptor)
    overrides_descriptor.prepare_defaults()

    assert overrides_descriptor.descriptor['run']['user'] == 123
