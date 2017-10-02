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
                logger.info("Using Docker builder to build the image.")
            elif 'osbs' == build_engine:
                # import is delayed until here to prevent circular import error
                from concreate.builders.osbs import OSBSBuilder as BuilderImpl
                logger.info("Using OSBS builder to build the image.")
            else:
                raise ConcreateError("Builder engine %s is not supported" % build_engine)

            return super(Builder, cls).__new__(BuilderImpl)

    def __init__(self, build_engine, target):
        self.target = target
        self.check_prerequisities()

    def check_prerequisities():
        pass

    def prepare(self, descriptor):
        # we dont require prepare to be implemented by builder
        pass

    def build(self, build_args):
        raise ConcreateError("Buider.build() is not implemented!")
