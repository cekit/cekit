
class Plugin(object):
    def __init__(self, dogen, args):
        self.dogen = dogen
        self.log = dogen.log
        self.descriptor = dogen.descriptor
        self.output = dogen.output
        self.args = args

    @staticmethod
    def inject_args(parser):
        return parser

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
