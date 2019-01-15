import logging
import os
import re
import yaml

from cekit.builder import Builder
from cekit.errors import CekitError

logger = logging.getLogger('cekit')

# Ignore any failure on non-core modules, we will catch it later
# and suggest a solution
try:
    # Squash library
    from docker_squash.squash import Squash
except ImportError:
    pass

try:
    # Docker Python library, the old one
    from docker.api.client import APIClient as APIClientClass
except ImportError:
    pass

try:
    # Docker Python library, the new one
    from docker.client import Client as APIClientClass
except ImportError:
    pass

ANSI_ESCAPE = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')


class DockerBuilder(Builder):
    """This class wraps docker build command to build and image"""

    def __init__(self, build_engine, target, params=None):
        if not params:
            params = {}
        self._tags = params.get('tags', [])
        self._pull = params.get('pull', False)
        self._base = params.get('base')
        super(DockerBuilder, self).__init__(build_engine, target, params)

        # Default Docker daemon connection timeout 10 minutes
        # It needs to be high enough to allow Docker daemon to export the
        # image for squashing.
        try:
            timeout = int(os.getenv('DOCKER_TIMEOUT', 600))
        except ValueError:
            raise CekitError("Provided timeout value: %s cannot be parsed as integer, exiting." %
                             os.getenv('DOCKER_TIMEOUT'))

        if not timeout > 0:
            raise CekitError(
                "Provided timeout value needs to be greater than zero, currently: %s, exiting." % timeout)

        self.docker_client = APIClientClass(version="1.22", timeout=timeout)

    @staticmethod
    def dependencies():
        deps = {}

        deps['python-docker'] = {
            'library': 'docker',
            'fedora': {
                'package': 'python3-docker',
                'command': 'rpm -q python3-docker'
            },
            'rhel': {
                'package': 'python-docker-py',
                'command': 'rpm -q python-docker-py'
            },
            'centos': {
                'package': 'python-docker-py',
                'command': 'rpm -q python-docker-py'
            }
        }

        deps['docker-squash'] = {
            'library': 'docker_squash',
            'fedora': {
                'package': 'python3-docker-squash',
                'command': 'rpm -q python3-docker-squash'
            }
        }

        return deps

    def build(self, build_args=None):
        """After the source files are generated, the container image can be built.
        We're using Docker to build the image currently.
        """
        args = {}
        args['path'] = os.path.join(self.target, 'image')
        args['tag'] = self._tags[0]
        args['pull'] = self._pull
        args['rm'] = True

        # Custom tags for the container image
        logger.debug("Building image with tags: '%s'" %
                     "', '".join(self._tags))

        logger.info("Building container image...")

        try:
            docker_layer_ids = []
            out = self.docker_client.build(**args)
            build_log = [""]
            for line in out:
                if b'stream' in line:
                    line = yaml.safe_load(line)['stream']
                elif b'status' in line:
                    line = yaml.safe_load(line)['status']
                elif b'errorDetail' in line:
                    line = yaml.safe_load(line)['errorDetail']['message']
                    raise CekitError("Image build failed: '%s'" % line)

                if line != build_log[-1]:
                    # this prevents poluting cekit log with dowloading/extracting msgs
                    log_msg = ANSI_ESCAPE.sub('', line).strip()
                    for msg in log_msg.split('\n'):
                        logger.info('Docker: %s' % msg)
                    build_log.append(line)

                    if '---> Running in ' in line:
                        docker_layer_ids.append(line.split(' ')[-1].strip())
                    elif 'Successfully built ' in line:
                        docker_layer_ids.append(line.split(' ')[-1].strip())
                    elif '---> Using cache' in build_log[-2]:
                        docker_layer_ids.append(line.split(' ')[-1].strip())

            self.squash_image(docker_layer_ids[-1])

            for tag in self._tags[1:]:
                if ':' in tag:
                    img_repo, img_tag = tag.split(":")
                    self.docker_client.tag(self._tags[0], img_repo, tag=img_tag)
                else:
                    self.docker_client.tag(self._tags[0], tag)
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

    def squash_image(self, layer_id):
        logger.info("Squashing image %s..." % (layer_id))
        # XXX: currently, cleanup throws a 409 error from the docker daemon.  this needs to be investigated in docker_squash
        squash = Squash(docker=self.docker_client, log=logger, from_layer=self._base, image=layer_id,
                        tag=self._tags[0],
                        cleanup=False)
        squash.run()
