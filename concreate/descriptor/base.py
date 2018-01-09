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
            self.descriptor = concreate.tools.merge_descriptors(self.descriptor, descriptor)
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


