from cekit.descriptor import Image, Execute
from cekit.descriptor.image import get_image_schema


class Module(Image):
    """Represents a module.

    Constructor arguments:
    descriptor_path: A path to module descriptor file.
    """

    def __init__(self, descriptor, path, artifact_dir):
        self._artifact_dir = artifact_dir
        self.path = path
        self.schema = get_image_schema().copy()
        # calling Descriptor constructor only here (we don't want Image() to mess with schema)
        super(Image, self).__init__(descriptor)
        self.skip_merging = ['description',
                             'version',
                             'name',
                             'release',
                             'help']

        self._prepare()
        self.name = self._descriptor['name']
        self._descriptor['execute'] = [Execute(x, self.name)
                                       for x in self._descriptor.get('execute', [])]

    @property
    def execute(self):
        return self.get('execute')
