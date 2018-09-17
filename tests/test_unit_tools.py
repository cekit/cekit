import pytest
import yaml

from cekit.descriptor.base import _merge_descriptors, _merge_lists
from cekit.descriptor import Descriptor, Image, Module, Overrides, Run
from cekit.errors import CekitError


class TestDescriptor(Descriptor):
    def __init__(self, descriptor):
        self.schemas = [yaml.safe_load("""type: any""")]
        super(TestDescriptor, self).__init__(descriptor)

        for key, val in descriptor.items():
            if isinstance(val, dict):
                self._descriptor[key] = TestDescriptor(val)


def test_merging_description_image():
    desc1 = Image({'name': 'foo', 'version': 1}, None)

    desc2 = Module({'name': 'mod1',
                    'description': 'mod_desc'}, None, None)

    merged = _merge_descriptors(desc1, desc2)
    assert 'description' not in merged


def test_merging_description_modules():
    desc1 = Module({'name': 'foo'}, None, None)

    desc2 = Module({'name': 'mod1',
                    'description': 'mod_desc'}, None, None)

    merged = _merge_descriptors(desc1, desc2)
    assert 'description' not in merged


def test_merging_description_override():
    desc1 = Image({'name': 'foo', 'version': 1}, None)

    desc2 = Overrides({'name': 'mod1',
                       'description': 'mod_desc'}, None)

    merged = _merge_descriptors(desc2, desc1)
    assert 'description' in merged


def test_merging_plain_descriptors():
    desc1 = TestDescriptor({'name': 'foo',
                            'a': 1,
                            'b': 2})

    desc2 = TestDescriptor({'name': 'foo',
                            'b': 5,
                            'c': 3})

    expected = TestDescriptor({'name': 'foo',
                               'a': 1,
                               'b': 2,
                               'c': 3})
    assert expected == _merge_descriptors(desc1, desc2)
    assert expected.items() == _merge_descriptors(desc1, desc2).items()


def test_merging_emdedded_descriptors():
    desc1 = TestDescriptor({'name': 'a',
                            'a': 1,
                            'b': {'name': 'b',
                                  'b1': 10,
                                  'b2': 20}})
    desc2 = TestDescriptor({'b': {'name': 'b',
                                  'b2': 50,
                                  'b3': 30},
                            'c': {'name': 'c'}})

    expected = TestDescriptor({'name': 'a',
                               'a': 1,
                               'b': {'name': 'b',
                                     'b1': 10,
                                     'b2': 20,
                                     'b3': 30},
                               'c': {'name': 'c'}})

    assert expected == _merge_descriptors(desc1, desc2)


def test_merging_plain_lists():
    list1 = [2, 3, 4, 5]
    list2 = [1, 2, 3]
    expected = [1, 2, 3, 4, 5]
    assert _merge_lists(list1, list2) == expected


def test_merging_plain_list_of_list():
    list1 = [1, 2, 3]
    list2 = [3, 4, []]
    with pytest.raises(CekitError):
        _merge_lists(list1, list2)


def test_merging_list_of_descriptors():
    desc1 = [TestDescriptor({'name': 1,
                             'a': 1,
                             'b': 2})]

    desc2 = [TestDescriptor({'name': 2,
                             'a': 123}),
             TestDescriptor({'name': 1,
                             'b': 3,
                             'c': 3})]

    expected = [TestDescriptor({'name': 2,
                                'a': 123}),
                TestDescriptor({'name': 1,
                                'a': 1,
                                'b': 2,
                                'c': 3})]

    assert expected == _merge_lists(desc1, desc2)


def test_merge_run_cmd():
    override = Run({'user': 'foo', 'cmd': ['a', 'b', 'c'], 'entrypoint': ['a', 'b']})
    image = Run({'user': 'foo', 'cmd': ['1', '2', '3'], 'entrypoint': ['1', '2']})

    override.merge(image)
    assert override['cmd'] == ['a', 'b', 'c']
    assert override['entrypoint'] == ['a', 'b']

    override = Run({})
    override.merge(image)
    assert override['cmd'] == ['1', '2', '3']
    assert override['entrypoint'] == ['1', '2']
    assert override['user'] == 'foo'
