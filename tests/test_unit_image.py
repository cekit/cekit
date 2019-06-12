import pytest
import yaml

from cekit.descriptor import Image, Packages, Overrides


def test_image_overrides_with_content_sets_none():
    image = Image(yaml.safe_load("""
    from: foo
    name: test/foo
    version: 1.9
    packages:
      install:
        - abc
        - def
      content_sets:
        arch:
          - namea
          - nameb
    """), 'foo')

    assert image.packages.content_sets == {'arch': ['namea', 'nameb']}
    assert 'content_sets_file' not in image.packages

    image.apply_image_overrides([Overrides({'packages': {'content_sets': None}}, "a/path")])

    assert 'content_sets' not in image.packages
    assert 'content_sets_file' not in image.packages


def test_image_overrides_with_content_sets_file_none(mocker):
    with mocker.mock_module.patch('cekit.descriptor.packages.os.path.exists') as exists_mock:
        exists_mock.return_value = True
        with mocker.mock_module.patch('cekit.descriptor.packages.open', mocker.mock_open(read_data='{"arch": ["a", "b"]}')):
            image = Image(yaml.safe_load("""
                from: foo
                name: test/foo
                version: 1.9
                packages:
                    install:
                        - abc
                         def
                    content_sets_file: cs.yaml
                """), 'foo')

    assert image.packages.content_sets == {'arch': ['a', 'b']}
    assert 'content_sets_file' not in image.packages

    image.apply_image_overrides([Overrides({'packages': {'content_sets_file': None}}, "a/path")])

    assert 'content_sets' not in image.packages
    assert 'content_sets_file' not in image.packages
