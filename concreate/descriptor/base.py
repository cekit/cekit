import concreate
import collections
import logging
import os
import yaml

from concreate.errors import ConcreateError
from pykwalify.core import Core

logger = logging.getLogger('concreate')


class Descriptor(collections.MutableMapping):
    def __init__(self, descriptor):
        self.skip_merging = []
        self._descriptor = descriptor
        self.__validate()

    def __validate(self):
        for schema in self.schemas:
            core = Core(source_data=self._descriptor,
                        schema_data=schema, allow_assertions=True)
            try:
                core.validate(raise_exception=True)
                return
            except Exception as ex:
                # We log this as debug, because we support multiple schemas
                logger.debug("Schema validation failed: %s" % ex)

        raise ConcreateError("Cannot validate schema: %s" % (self.__class__.__name__))

    def write(self, path):
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(path, 'w') as outfile:
            yaml.dump(self._descriptor, outfile, default_flow_style=False)

    def label(self, key):
        for l in self._descriptor['labels']:
            if l['name'] == key:
                return l
        return None

    def merge(self, descriptor):
        """ Merges two descriptors in a way, that arrays are appended
        and duplicit values are kept
        Args:
          descriptor - a concreate descritor
        """
        try:
            _merge_descriptors(self, descriptor)
        except KeyError as ex:
            logger.debug(ex, exc_info=True)
            raise ConcreateError("Cannot merge descriptors, see log message for more information")

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self['name'] == other['name']
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self['name'] == other['name']
        return NotImplemented

    def __getitem__(self, key):
        return self._descriptor[key]

    def __setitem__(self, key, item):
        self._descriptor[key] = item

    def __delitem__(self, key):
        del self._descriptor[key]

    def __iter__(self):
        return self._descriptor.__iter__()

    def __len__(self):
        return len(self._descriptor)

    def items(self):
        return self._descriptor.items()

    def get(self, k, default=None):
        return self._descriptor.get(k, default)

    def process_defaults(self):
        """Prepares default values before rendering"""
        if 'execute' in self._descriptor:
            for execute in self._descriptor['execute']:
                if 'user' not in execute:
                    execute['user'] = concreate.DEFAULT_USER

        if 'run' not in self._descriptor:
            self._descriptor['run'] = {}

        if 'user' not in self._descriptor['run']:
            self._descriptor['run']['user'] = concreate.DEFAULT_USER


def _merge_descriptors(desc1, desc2):
    """
    Merges two descriptors with handling embedded lists and
    descriptors.

    Args:
      desc1, desc2: descriptors to merge

    Return merged descriptor
    """
    for k2, v2 in desc2.items():
        if k2 not in desc1:
            desc1[k2] = v2
        else:
            if isinstance(v2, list):
                desc1[k2] = _merge_lists(desc1[k2], v2)
            elif isinstance(v2, Descriptor):
                desc1[k2] = _merge_descriptors(desc1[k2], v2)
    return desc1


def _merge_lists(list1, list2):
    """ Merges two lists handling embedded dictionaries via 'name' as a key
    In a case of simple type values are appended.

    Args:
      list1, list2 - list to merge

    Returns merged list
    """
    for v2 in list2:
        if isinstance(v2, Descriptor):
            if v2 in list1:
                _merge_descriptors(list1[list1.index(v2)], v2)
            else:
                list1.append(v2)
        elif isinstance(v2, list):
            raise ConcreateError("Cannot merge list of lists")
        else:
            if v2 not in list1:
                list1.append(v2)
    return list1
