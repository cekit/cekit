import docker
import logging
import os
import re
import yaml

from cekit.builder import Builder
from cekit.errors import CekitError

try:
    docker_client = docker.Client(version="1.22")
except AttributeError:
    docker_client = docker.APIClient(version="1.22")

logger = logging.getLogger('cekit')

ANSI_ESCAPE = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')


class DockerBuilder(Builder):
    """This class wraps docker build command to build and image"""

    def __init__(self, build_engine, target, params=None):
        if not params:
            params = {}
        self._tags = params.get('tags', [])
        self._pull = params.get('pull', False)
        super(DockerBuilder, self).__init__(build_engine, target, params)

    def check_prerequisities(self):
        try:
            docker_client.images
        except Exception as ex:
            raise CekitError("Docker build engine needs docker with python bindings installed "
                             " and configured, error: %s" % ex)

    def build(self, build_args=None):
        """After the source files are generated, the container image can be built.
        We're using Docker to build the image currently.
        """
        args = {}
        args['path'] = os.path.join(self.target, 'image')
        args['tag'] = self._tags[0]
        args['pull'] = self._pull

        # Custom tags for the container image
        logger.debug("Building image with tags: '%s'" %
                     "', '".join(self._tags))

        logger.info("Building container image...")

        try:
            docker_layer_ids = []
            out = docker_client.build(**args)
            build_log = [""]
            for line in out:
                if b'stream' in line:
                    line = yaml.safe_load(line)['stream']
                elif b'status' in line:
                    line = yaml.safe_load(line)['status']
                elif b'errorDetail' in line:
                    line = yaml.safe_load(line)['errorDetail']['message']
                    raise CekitError("Image build failed: '%s'" % line)

                if '---> Running in ' in line:
                    docker_layer_ids.append(line.split(' ')[-1])

                if '---> Using cache' in build_log[-1]:
                    docker_layer_ids.append(line.split(' ')[-1])

                if line != build_log[-1]:
                    # this prevents poluting cekit log with dowloading/extracting msgs
                    log_msg = ANSI_ESCAPE.sub('', line).strip()
                    for msg in log_msg.split('\n'):
                        logger.info('Docker: %s' % msg)
                    build_log.append(line)

            for tag in self._tags[1:]:
                if ':' in tag:
                    img_repo, img_tag = tag.split(":")
                    docker_client.tag(self._tags[0], img_repo, tag=img_tag)
                else:
                    docker_client.tag(self._tags[0], tag)
            logger.info("Image built and available under following tags: %s"
                        % ", ".join(self._tags))

        except Exception as ex:
            msg = "Image build failed, see logs above."
            if len(docker_layer_ids) >= 2:
                logger.error("You can look inside the failed image by running "
                             "'docker run --rm -ti %s bash'" % docker_layer_ids[-2])
            if "To enable Red Hat Subscription Management repositories:" in ' '.join(build_log) and \
               not os.path.exists(os.path.join(self.target, 'image', 'repos')):
                msg = "Image build failed with a yum error and you don't " \
                    "have any yum repository configured, please check " \
                    "your image/module descriptor for proper repository " \
                    " definitions."
            raise CekitError(msg, ex)
