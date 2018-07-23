import logging

from cekit.errors import CekitError

logger = logging.getLogger('cekit')


class Builder(object):
    """Class representing generic builder - if its instantiated it returns proper builder
    Args:
      build_engine - a build engine to use to build image
      image_dir - path where image sources are generated
      params - a dictionary of builder specific parameters
    """

    def __new__(cls, build_engine, target, params={}):
        if cls is Builder:
            if 'docker' == build_engine:
                # import is delayed until here to prevent circular import error
                from cekit.builders.docker_builder import DockerBuilder as BuilderImpl
                logger.info("Using Docker builder to build the image.")
            elif 'osbs' == build_engine:
                # import is delayed until here to prevent circular import error
                from cekit.builders.osbs import OSBSBuilder as BuilderImpl
                logger.info("Using OSBS builder to build the image.")
            elif 'buildah' == build_engine:
                from cekit.builders.buildah import BuildahBuilder as BuilderImpl
                logger.info("Using Buildah builder to build the image.")
            else:
                raise CekitError("Builder engine %s is not supported" % build_engine)

            return super(Builder, cls).__new__(BuilderImpl)

    def __init__(self, build_engine, target, params={}):
        self.target = target
        self.check_prerequisities()

    def check_prerequisities():
        pass

    def prepare(self, descriptor):
        # we dont require prepare to be implemented by builder
        pass

    def build(self, build_args):
        raise CekitError("Buider.build() is not implemented!")
