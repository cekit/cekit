import pytest
import yaml

from concreate import tools
from concreate.descriptor import Descriptor
from concreate.errors import ConcreateError


class TestDescriptor(Descriptor):
    def __init__(self, descriptor):
        self.schemas = [yaml.safe_load("""type: any""")]
        super(TestDescriptor, self).__init__(descriptor)

        for key, val in descriptor.items():
            if isinstance(val, dict):
                self.descriptor[key] = TestDescriptor(val)


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
    assert expected == tools.merge_descriptors(desc1, desc2)
    assert expected.items() == tools.merge_descriptors(desc1, desc2).items()


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

    assert expected == tools.merge_descriptors(desc1, desc2)


def test_merging_plain_lists():
    list1 = [1, 2, 3]
    list2 = [2, 3, 4, 5]
    expected = [1, 2, 3, 4, 5]
    assert tools.merge_lists(list1, list2) == expected


def test_merging_plain_list_of_list():
    list1 = [1, 2, 3]
    list2 = [3, 4, []]
    with pytest.raises(ConcreateError):
        tools.merge_lists(list1, list2)


def test_merging_list_of_descriptors():
    desc1 = [TestDescriptor({'name': 1,
                             'a': 1,
                             'b': 2})]

    desc2 = [TestDescriptor({'name': 2,
                             'a': 123}),
             TestDescriptor({'name': 1,
                             'b': 3,
                             'c': 3})]

    expected = [TestDescriptor({'name': 1,
                                'a': 1,
                                'b': 2,
                                'c': 3}),
                TestDescriptor({'name': 2,
                                'a': 123})]

    assert expected == tools.merge_lists(desc1, desc2)
