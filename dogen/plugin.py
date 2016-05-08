
class Plugin(object):
    @classmethod
    def list(cls):
        return cls.__subclasses__()

    def __init__(self, dogen):
        self.dogen = dogen
        self.log = dogen.log
        self.descriptor = dogen.descriptor
        self.output = dogen.output

    def prepare(self, **kwargs):
        pass

    def after_sources(self, **kwargs):
        pass
