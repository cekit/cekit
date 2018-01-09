import concreate

from concreate.descriptor import Image, Execute
from concreate.descriptor.image import image_schema


module_schema = image_schema.copy()
module_schema['map']['name'] = {'type': 'str'}
module_schema['map']['version'] = {'type': 'text'}
module_schema['map']['execute'] = {'type': 'any'}


class Module(Image):
    """Represents a module.

    Constructor arguments:
    descriptor_path: A path to module descriptor file.
    """
    def __init__(self, descriptor, path):
        schema = module_schema.copy()
        self.schemas = [schema]
        # calling Descriptor constructor only here (we dont wat Image() to mess with schema)
        super(Image, self).__init__(descriptor)

        self._prepare()
        self.path = path
        self.name = self._descriptor['name']
        self._descriptor['execute'] = [Execute(x, self.name)
                                      for x in self._descriptor.get('execute', [])]

    def fetch_dependencies(self, repo_root):
        """ Processes modules dependencies and fetches them.

        Arguments:
        repo_root: A parent directory where repositories will be cloned in
        """
        concreate.module.get_dependencies(self._descriptor, repo_root)
