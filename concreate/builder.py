import logging

from concreate.errors import ConcreateError

logger = logging.getLogger('concreate')


class Builder(object):
    """Class representing generic builder - if its instantiated it returns proper builder
    Args:
      build_engine - a build engine to use to build image
      image_dir - path where image sources are generated
    """

    def __new__(cls, build_engine, target):
        if cls is Builder:
            if 'docker' == build_engine:
                # import is delayed until here to prevent circular import error
                from concreate.builders.docker import DockerBuilder as BuilderImpl
            elif 'osbs' == build_engine:
                # import is delayed until here to prevent circular import error
                from concreate.builders.osbs import OSBSBuilder as BuilderImpl
            else:
                raise ConcreateError("Builder engine %s is not supported" % build_engine)

            return super(Builder, cls).__new__(BuilderImpl)

    def __init__(self, build_engine, target):
        self.target = target

    def prepare(self, descriptor):
        # we dont require prepare to be implemented by builder
        pass

    def build(self, build_tags=[]):
        raise ConcreateError("Buider.build() is not implemented!")
