import yaml

import cekit

from cekit.descriptor import Descriptor


execute_schemas = [yaml.safe_load("""
        map:
          name: {type: str}
          script: {type: str}
          user: {type: text}""")]

container_schemas = [yaml.safe_load("""
        seq:
          - {type: any}""")]


class Execute(Descriptor):
    def __init__(self, descriptor, module_name):
        self.schemas = execute_schemas
        super(Execute, self).__init__(descriptor)

        descriptor['directory'] = module_name

        if 'user' not in descriptor:
            descriptor['user'] = cekit.DEFAULT_USER

        descriptor['module_name'] = module_name

        if 'name' not in descriptor:
            descriptor['name'] = "%s/%s" % (module_name,
                                            descriptor['script'])


class ExecuteContainer(Descriptor):
    """Container holding Execute classes. I't responsible for correct
    Execute Class merging and ordering"""

    def __init__(self, descriptor, module_name):
        self.schemas = container_schemas
        super(ExecuteContainer, self).__init__(descriptor)
        self.name = module_name
        if not descriptor:
            descriptor = [{'name': 'noop'}]

        self._descriptor = [Execute(x, module_name) for x in descriptor]

    def _get_real_executes(self):
        return [x for x in self._descriptor if x['name'] != 'noop']

    def __len__(self):
        return len(self._get_real_executes())

    def __iter__(self):
        return iter(self._get_real_executes())

    def merge(self, descriptor):
        """To merge modules in correct order we need to insert
        new executes before the last module. This the raeson why noop
        execut exists"""

        prev_module = self._descriptor[-1]['module_name']
        pos = 0
        for executes in self._descriptor:
            if executes['module_name'] == prev_module:
                continue
            pos += 1

        for executes in reversed(list(descriptor)):
            if executes not in self._descriptor:
                self._descriptor.insert(pos, executes)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        for i, execute in enumerate(self._descriptor):
            if execute != other[i]:
                return False

        return True
