import logging
import os

from concreate import DEFAULT_USER
from concreate.errors import ConcreateError
from concreate.tools import load_descriptor
from concreate.version import schema_version

logger = logging.getLogger('concreate')


class Descriptor(object):
    """ Representes a module/image descriptor
    Args:
      descriptor_path - a path to the image/module descriptor
      descriptor_type - a type of descriptor (image/module)
    """

    def __init__(self, descriptor_path, descriptor_type):
        self.directory = os.path.dirname(descriptor_path)
        self.descriptor = load_descriptor(descriptor_path, descriptor_type)
        if descriptor_type == 'image':
            self.check_schema_version()

    def check_schema_version(self):
        """ Check supported schema version """
        if self.descriptor['schema_version'] != schema_version:
            raise ConcreateError("Schema version: '%s' is not supported by current version."
                                 " This version supports schema version: '%s' only."
                                 " To build this image please install concreate version: '%s'"
                                 % (self.descriptor['schema_version'],
                                    schema_version,
                                    self.descriptor['schema_version']))

    def __getitem__(self, key):
        return self.descriptor[key]

    def __setitem__(self, key, item):
        self.descriptor[key] = item

    def __iter__(self):
        return self.descriptor.__iter__()

    def items(self):
        return self.descriptor.items()

    def process(self):
        """ Prepare descriptor to be used by generating defaults """
        if 'artifacts' in self.descriptor:
            self._process_artifacsts()
        if 'execute' in self.descriptor:
            self._process_execute()
        if 'ports' in self.descriptor:
            self._process_ports()
        if 'dependencies' in self.descriptor:
            self._process_dependencies()
        self._process_labels()
        return self

    def merge(self, descriptor):
        """ Merges two descriptors in a way, that arrays are appended
        and duplicit values are kept

        Args:
          descriptor - a concreate descritor
        """
        try:
            self.descriptor = merge_dictionaries(self.descriptor, descriptor)
        except KeyError as ex:
            logger.debug(ex, exc_info=True)
            raise ConcreateError("Dictionary is missing 'name' keyword")

    def _process_artifacsts(self):
        """ Processes descriptor artifacts section and generate default
        value 'name' for each artifact which doesnt have 'name' specified.
        """
        for artifact in self.descriptor['artifacts']:
            if 'name' not in artifact:
                artifact['name'] = os.path.basename(artifact['artifact'])

    def _process_execute(self):
        """ Prepares executables of modules to contian all needed data like,
        directories, module name, unique name
        """
        for execute in self.descriptor['execute']:
            module = self.descriptor['name']
            execute['directory'] = module
            execute['name'] = "%s-%s" % (module,
                                         execute['execute'])
            if 'user' not in execute:
                execute['user'] = DEFAULT_USER

    def _process_ports(self):
        """ Generate name attribute for ports """
        for port in self.descriptor['ports']:
            port['name'] = port['value']

    def _process_dependencies(self):
        """ Generate name attribute for dependencies """
        for dependency in self.descriptor['dependencies']:
            if 'name' not in dependency:
                dependency['name'] = os.path.basename(dependency['url'])

    def _process_labels(self):
        """ Generate labels from concreate keys """
        if "labels" not in self.descriptor:
            self.descriptor['labels'] = []
        if "description" in self.descriptor:
            self.descriptor['labels'].append({'name': 'description',
                                              'value': self.descriptor['description']})


def merge_dictionaries(dict1, dict2):
    """ Merges two dictionaries handling embedded lists and
    dictionaries.
    In a case of simple type, values from dict1 are preserved.

    Args:
      dict1, dict2 dictionaries to merge

    Return merged dictionaries
    """
    for k2, v2 in dict2.items():
        if k2 not in dict1:
            dict1[k2] = v2
        else:
            if isinstance(v2, list):
                dict1[k2] = merge_lists(dict1[k2], v2)
            elif isinstance(v2, dict):
                dict1[k2] = merge_dictionaries(dict1[k2], v2)
            else:
                # if the type is int or strings we do nothing
                # its already in dict1
                pass
    return dict1


def merge_lists(list1, list2):
    """ Merges two lists handling embedded dictionaries via 'name' as a key
    In a case of simple type values are appended.

    Args:
      list1, list2 - list to merge

    Returns merged list
    """
    list1_dicts = [x for x in list1 if isinstance(x, dict)]
    for v2 in list2:
        if isinstance(v2, dict):
            if v2['name'] not in [x['name'] for x in list1_dicts]:
                list1.append(v2)
            else:
                for v1 in list1_dicts:
                    if v2['name'] == v1['name']:
                        merge_dictionaries(v1, v2)
        elif isinstance(v2, list):
            raise ConcreateError("Cannot merge list of lists")
        else:
            if v2 not in list1:
                list1.append(v2)
    return list1
