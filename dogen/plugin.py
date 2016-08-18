
class Plugin(object):
    def __init__(self, dogen):
        self.dogen = dogen
        self.log = dogen.log
        self.descriptor = dogen.descriptor
        self.output = dogen.output

    def prepare(self, **kwargs):
        pass

    def after_sources(self, **kwargs):
        pass

    def extend_schema(self, schema):
        """
        Plugins have an opportunity to extend the schema used to validate
        the dogen YAML configuration, to support additional keys that the
        plugin might need.
        """
        pass
