import unittest

from concreate import tools
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
                         tools.merge_dictionaries(dict1, dict2))

    def test_merging_plain_dictionaries_for_kwalify_schema(self):
        dict1 = {'a': 1,
                 'b': 2}
        dict2 = {'b': 5,
                 'c': 3}
        expected = {'a': 1,
                    'b': 5,
                    'c': 3}
        self.assertEqual(expected,
                         tools.merge_dictionaries(dict1, dict2, True))

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
                         tools.merge_dictionaries(dict1, dict2))


class TestMergingLists(unittest.TestCase):

    def test_merging_plain_lists(self):
        list1 = [1, 2, 3]
        list2 = [2, 3, 4, 5]
        expected = [1, 2, 3, 4, 5]
        self.assertEqual(tools.merge_lists(list1, list2),
                         expected)

    def test_merging_plain_list_of_list(self):
        list1 = [1, 2, 3]
        list2 = [3, 4, []]
        with self.assertRaises(ConcreateError):
            tools.merge_lists(list1, list2)

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
                         tools.merge_lists(list1, list2))
