import copy

from cekit.descriptor import Image
from cekit.descriptor.image import get_image_schema

overrides_schema = get_image_schema()
overrides_schema["map"]["name"] = {"type": "str"}
overrides_schema["map"]["version"] = {"type": "text"}


class Overrides(Image):
    def __init__(self, descriptor, artifact_dir):
        self.original_descriptor = copy.deepcopy(descriptor)
        self._artifact_dir = artifact_dir
        self.path = artifact_dir
        schema = overrides_schema.copy()
        self.schema = schema
        # calling Descriptor constructor only here (we don't want Image() to mess with schema)
        super(Image, self).__init__(descriptor)

        self._prepare()
