import logging
import os
import re
import tempfile
import traceback
from pathlib import Path
from typing import List

from cekit.builders.oci_builder import OCIBuilder
from cekit.cekit_types import DependencyDefinition
from cekit.errors import CekitError
from cekit.tools import locate_binary, parse_env_timeout

LOGGER = logging.getLogger("cekit")

# Ignore any failure on non-core modules, we will catch it later
# and suggest a solution
try:
    # Squash library
    from docker_squash.squash import Squash
except ModuleNotFoundError:
    pass

try:
    # Docker Python library, the new one
    import docker
except ModuleNotFoundError:
    pass

try:
    # The requests library is an indirect dependency, we need to put it here
    # so that the dependency mechanism can kick in and require the docker library
    # first which will pull requests
    import requests
except ModuleNotFoundError:
    pass

ANSI_ESCAPE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
DOCKER_API_VERSION = "1.35"


class DockerBuilder(OCIBuilder):
    """This class wraps docker build command to build and image"""

    def __init__(self, params):
        super(DockerBuilder, self).__init__("docker", params)

    @staticmethod
    def dependencies(params=None) -> DependencyDefinition:
        deps = {}

        deps["python-docker"] = {
            "library": "docker",
            "package": "python3-docker",
            "centos7": {"package": "python36-docker"},
        }

        if params is not None and not params.no_squash:
            deps["docker-squash"] = {
                "library": "docker_squash",
                "fedora": {"package": "python3-docker-squash"},
            }

        return deps

    def _build_with_docker(self, docker_client):
        docker_args = {}
        docker_args["decode"] = True
        docker_args["path"] = os.path.join(self.target, "image")
        docker_args["pull"] = self.params.pull
        docker_args["rm"] = True
        if self.params.build_args:
            buildargs = {}
            for arg in self.params.build_args:
                if "=" in arg:
                    split = arg.split("=")
                    buildargs.update({split[0]: split[1]})
                else:
                    buildargs.update({arg: None})
            docker_args["buildargs"] = buildargs

        build_log = []
        docker_layer_ids = []

        LOGGER.debug(f"Running Docker build: {str(docker_args)}")
        try:
            stream = docker_client.build(**docker_args)

            for part in stream:
                # In case an error is returned, log the message and fail the build
                if "errorDetail" in part:
                    error_message = part.get("errorDetail", {}).get("message", "")
                    raise CekitError(f"Image build failed: '{error_message}'")
                elif "stream" in part:
                    messages = part["stream"]
                else:
                    # We actually expect only 'stream' here.
                    # If there is something different, we ignore it.
                    # It's safe to do so because if it would be an error, we would catch it
                    # earlier. Ignored logs are related to fetching/pulling/extracting
                    # of container images.
                    continue

                # This prevents polluting CEKit log with downloading/extracting messages
                messages = ANSI_ESCAPE.sub("", messages).strip()

                for message in messages.split("\n"):
                    LOGGER.info(f"Docker: {message}")

                build_log.append(messages)

                layer_id_match = re.search(r"^---> ([\w]{12})$", messages)

                if layer_id_match:
                    docker_layer_ids.append(layer_id_match.group(1))

        except requests.ConnectionError:
            exception_chain = traceback.format_exc()
            LOGGER.debug(
                "Caught ConnectionError attempting to communicate with Docker ",
                exc_info=True,
            )

            if "PermissionError" in exception_chain:
                message = (
                    "Unable to contact docker daemon. Is it correctly setup?\n"
                    "See https://developer.fedoraproject.org/tools/docker/docker-installation.html and "
                    "http://www.projectatomic.io/blog/2015/08/why-we-dont-let-non-root-users-run-docker-in-centos-fedora-or-rhel"
                )
            elif "FileNotFoundError" in exception_chain:
                message = "Unable to contact docker daemon. Is it started?"
            else:
                message = "Unknown ConnectionError from docker ; is the daemon started and correctly setup?"

            raise CekitError(message) from None

        except Exception as ex:
            msg = "Image build failed, see logs above."
            if len(docker_layer_ids) >= 2:
                LOGGER.error(
                    "You can look inside the failed image by running "
                    "'docker run --rm -ti {} bash'".format(docker_layer_ids[-1])
                )
            if "To enable Red Hat Subscription Management repositories:" in " ".join(
                build_log
            ) and not os.path.exists(os.path.join(self.target, "image", "repos")):
                msg = (
                    "Image build failed with a yum error and you don't "
                    "have any yum repository configured, please check "
                    "your image/module descriptor for proper repository "
                    "definitions."
                )
            LOGGER.error(ex)
            raise CekitError(msg) from ex

        return docker_layer_ids[-1]

    def _squash(self, docker_client, image_id, squash_all_layers=False):
        LOGGER.info(f"Squashing image {image_id}...")

        if squash_all_layers:
            layer = None
        else:
            layer = self.generator.image["from"]
        squash = Squash(
            docker=docker_client,
            log=LOGGER,
            from_layer=layer,
            image=image_id,
            cleanup=True,
        )
        return squash.run()

    def _tag(self, docker_client, image_id, tags):
        for tag in tags:
            if ":" in tag:
                img_repo, img_tag = tag.rsplit(":", 1)
                docker_client.tag(image_id, img_repo, tag=img_tag)
            else:
                docker_client.tag(image_id, tag)

    def _docker_client(self):
        LOGGER.debug("Preparing Docker client...")

        # Default Docker daemon connection timeout 10 minutes
        # It needs to be high enough to allow Docker daemon to export the
        # image for squashing.
        timeout = parse_env_timeout("DOCKER_TIMEOUT", "600")

        params = {"version": DOCKER_API_VERSION}
        params.update(docker.utils.kwargs_from_env())
        params["timeout"] = timeout

        try:
            client = docker.APIClient(**params)
        except docker.errors.DockerException as e:
            LOGGER.error(
                "Could not create Docker client, please make sure that you "
                "specified valid parameters in the 'DOCKER_HOST' environment variable, "
                "examples: 'unix:///var/run/docker.sock', 'tcp://192.168.22.33:1234'"
            )
            raise CekitError("Error while creating the Docker client") from e

        if client and self._valid_docker_connection(client):
            LOGGER.debug("Docker client ready and working")
            LOGGER.debug(client.version())
            return client

        LOGGER.error(
            "Could not connect to the Docker daemon at '{}', please make sure the Docker "
            "daemon is running.".format(client.base_url)
        )

        if client.base_url.startswith("unix"):
            LOGGER.error("Please make sure the Docker socket has correct permissions.")

        if os.environ.get("DOCKER_HOST"):
            LOGGER.error(
                "If Docker daemon is running, please make sure that you specified valid "
                "parameters in the 'DOCKER_HOST' environment variable, examples: "
                "'unix:///var/run/docker.sock', 'tcp://192.168.22.33:1234'. You may "
                "also need to specify 'DOCKER_TLS_VERIFY', and 'DOCKER_CERT_PATH' "
                "environment variables."
            )

        raise CekitError("Cannot connect to Docker daemon")

    def _valid_docker_connection(self, client):
        try:
            return client.ping()
        except requests.exceptions.ConnectionError:
            pass

        return False

    def run(self):
        tags = self.params.tags

        if not tags:
            tags = self.generator.get_tags()

        LOGGER.debug("Building image with tags: '{}'".format("', '".join(tags)))
        LOGGER.info("Building container image...")

        docker_client = self._docker_client()

        if self.params.platform or self.params.build_flag:
            cmd: List[str] = [locate_binary("docker"), "build"]
            with tempfile.NamedTemporaryFile() as tmp:
                cmd.append(f"--iidfile={tmp.name}")
                # Don't tag in the common_build as it leads to image reference issues
                self.common_build("docker", cmd, False)
                # Strip "sha256:" from the start
                image_id = Path(tmp.name).read_text()[7:]
            if not self.params.no_squash:
                # Docker buildkit does not show history so squash without a from reference
                # https://github.com/moby/buildkit/issues/1235
                image_id = self._squash(docker_client, image_id, True)
        else:
            # Build image
            image_id = self._build_with_docker(docker_client)

            # Squash only if --no-squash is NOT defined
            if not self.params.no_squash:
                image_id = self._squash(docker_client, image_id)

        # Tag the image
        self._tag(docker_client, image_id, tags)

        LOGGER.info(
            f"Image ID {image_id} built and available under following tags: {', '.join(tags)}"
        )
