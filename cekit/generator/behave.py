from cekit.generator.base import Generator


class BehaveGenerator(Generator):
    def __init__(self, descriptor_path, target, overrides):
        super(BehaveGenerator, self).__init__(descriptor_path, target, overrides)

    def prepare_artifacts(self):
        pass
