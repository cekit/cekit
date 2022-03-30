import logging
import os
from collections.abc import MutableMapping

import yaml
from pykwalify.core import Core
from pykwalify.errors import SchemaError

from cekit.errors import CekitError

logger = logging.getLogger("cekit")


class Descriptor(MutableMapping):
    """Class serving as parent for any descriptor in cekit.

    Class implement collections.MutableMapping so it can be used as a dictionary.

    * Schema validation:
    Each class which uses this as a parent can validate its schemas defined in
    self.schemas by calling Descriptor constructor

    * Merging
    Any two Descriptor childs can be merged by invoking merge() method. Each subclass
    can define its own logic for merging by overriding this method.
    If there is any key which should not be merged, it should be appended to Descriptor.skip_merging
    list.

    args:
      descriptor - an descriptor to be represented by this class

    """

    def __init__(self, descriptor):
        self.skip_merging = []
        self._descriptor = descriptor
        self.__validate()

    def __validate(self):
        if not self.schema:
            return

        try:
            core = Core(
                source_data=self._descriptor,
                schema_data=self.schema,
                allow_assertions=True,
            )

            core.validate(raise_exception=True)
        except SchemaError as ex:
            raise CekitError(
                "Cannot validate schema: {}".format(self.__class__.__name__), ex
            )

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_data(node._descriptor)

    def write(self, path):
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(path, "w") as outfile:
            yaml.SafeDumper.add_multi_representer(Descriptor, Descriptor.to_yaml)
            yaml.dump(
                self._descriptor,
                outfile,
                default_flow_style=False,
                Dumper=yaml.SafeDumper,
            )

    def label(self, key):
        for ll in self._descriptor["labels"]:
            if ll["name"] == key:
                return ll
        return None

    def merge(self, descriptor):
        """Merges two descriptors in a way, that arrays are appended
        and duplicate values are kept
        Args:
          descriptor - a cekit descriptor
        """
        try:
            _merge_descriptors(self, descriptor)
            return self
        except KeyError as ex:
            logger.debug(ex, exc_info=True)
            raise CekitError(
                "Cannot merge descriptors, see log message for more information"
            )

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self["name"] == other["name"]
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self["name"] == other["name"]
        return NotImplemented

    def __getattr__(self, name):
        """
        Make it possible to access the descriptor map as
        a property:

            o.name instead of o['name']

        If an attribute is assigned to the object and to the
        descriptor, object attribute wins and is returned.
        """

        try:
            return super(Descriptor, self).__getattr__(name)
        except AttributeError:
            pass

        if name in self._descriptor:
            return self._descriptor[name]

        return None

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

    def __repr__(self):
        return "%s" % self._descriptor

    def get(self, k, default=None):
        return self._descriptor.get(k, default)

    def process_defaults(self):
        pass

    def remove_none_keys(self):
        if isinstance(self, Descriptor):
            _remove_none_keys(self)
        else:
            # it means it list
            for desc in self:
                _remove_none_keys(desc)


def _remove_none_keys(desc):
    for key in dict(desc.items()):
        if isinstance(desc[key], Descriptor):
            desc[key].remove_none_keys()
        if isinstance(desc[key], list):
            for d in desc[key]:
                if isinstance(d, Descriptor):
                    d.remove_none_keys()
        elif desc[key] is None:
            del desc[key]


def _merge_descriptors(desc1, desc2):
    """
    Merges two descriptors with handling embedded lists and
    descriptors.

    Args:
      desc1, desc2: descriptors to merge

    Return merged descriptor
    """
    if desc2 is None:
        return desc1
    for k2, v2 in desc2.items():
        if k2 in desc1.skip_merging:
            continue
        if k2 not in desc1:
            desc1[k2] = v2
        else:
            if isinstance(v2, Descriptor):
                desc1[k2].merge(v2)
            elif isinstance(v2, list):
                desc1[k2] = _merge_lists(desc1[k2], v2)

    return desc1


def _merge_lists(list1, list2):
    """Merges two lists handling embedded dictionaries via 'name' as a key
    In a case of simple type values are appended.

    Args:
      list1, list2 - list to merge

    Returns merged list
    """
    for v2 in reversed(list2):
        if isinstance(v2, Descriptor):
            if v2 in list1:
                v1 = list1.pop(list1.index(v2))
                list1.insert(0, v1.merge(v2))
            else:
                list1.insert(0, v2)
        elif isinstance(v2, list):
            raise CekitError("Cannot merge list of lists")
        else:
            if v2 not in list1:
                list1.insert(0, v2)

    return list1
