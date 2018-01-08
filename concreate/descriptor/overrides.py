from concreate.descriptor import Image
from concreate.descriptor.image import image_schema

overrides_schema = image_schema.copy()
overrides_schema['map']['name'] = {'type': 'str'}
overrides_schema['map']['version'] = {'type': 'text'}


class Overrides(Image):
    def __init__(self, descriptor):
        schema = overrides_schema.copy()
        self.schemas = [schema]
        # calling Descriptor constructor only here (we dont wat Image() to mess with schema)
        super(Image, self).__init__(descriptor)

        self._prepare()
