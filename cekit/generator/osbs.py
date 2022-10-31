import fileinput
import logging
import os
import sys
import tempfile
from collections import OrderedDict
from contextlib import closing
from typing import Dict, List
from urllib.parse import urlparse

import yaml

from cekit import crypto, version
from cekit.config import Config
from cekit.descriptor.resource import (
    Resource,
    _PlainResource,
    _PncResource,
    _UrlResource,
)
from cekit.errors import CekitError
from cekit.generator.base import Generator
from cekit.tools import copy_recursively, get_brew_url

logger = logging.getLogger("cekit")
config = Config()


class OSBSGenerator(Generator):
    def __init__(self, descriptor_path, target, overrides):
        self._wipe = True
        super(OSBSGenerator, self).__init__(descriptor_path, target, overrides)

    def init(self):
        super(OSBSGenerator, self).init()

        self._prepare_osbs_config_file(yaml.safe_dump, "container.yaml")
        self._prepare_osbs_config_file(
            lambda contents, file, **kwargs: file.write(contents), "gating.yaml"
        )

    def generate(self):
        # If extra directory exists (by default named 'osbs_extra') next to
        # the image descriptor, copy it contents to the target directory.
        #
        # https://github.com/cekit/cekit/issues/394
        copy_recursively(
            os.path.join(
                os.path.dirname(self._descriptor_path), self.image.osbs.extra_dir
            ),
            os.path.join(self.target, os.path.join("image", self.image.osbs.extra_dir)),
        )
        super(OSBSGenerator, self).generate()

    def _prepare_content_sets(self, content_sets):
        content_sets_f = os.path.join(self.target, "image", "content_sets.yml")

        if not os.path.exists(os.path.dirname(content_sets_f)):
            os.makedirs(os.path.dirname(content_sets_f))

        with open(content_sets_f, "w") as _file:
            yaml.safe_dump(content_sets, _file, default_flow_style=False)

    def _prepare_osbs_config_file(self, writer, config_file):
        config_path = os.path.join(self.target, "image", config_file)
        config_name = config_file.split(".")[0]
        all_configs = []

        if self.image.get("osbs", {}).get("configuration", {}).get(config_name):
            all_configs.append(
                self.image.get("osbs", {}).get("configuration", {}).get(config_name)
            )

        # Check all images (for multi-stage) if they contain a container definition
        for i in self.builder_images:
            if i.get("osbs", {}).get("configuration", {}).get(config_name):
                all_configs.append(
                    i.get("osbs", {}).get("configuration", {}).get(config_name, {})
                )

        if len(all_configs) > 1:
            logger.error(
                "Found multiple {} definitions ({})".format(config_name, all_configs)
            )
            raise CekitError(
                "Found multiple {} definitions ({})!".format(config_name, all_configs)
            )
        elif len(all_configs) == 0:
            return

        logger.debug(
            "Writing to {} using ident of {} with content {}".format(
                config_path, config_name, all_configs[0]
            )
        )
        if not os.path.exists(os.path.dirname(config_path)):
            os.makedirs(os.path.dirname(config_path))
        with open(config_path, "w") as _file:
            writer(all_configs[0], _file, default_flow_style=False)

    def prepare_artifacts(self):
        """Goes through artifacts section of image descriptor
        and fetches all of them
        """

        logger.info("Handling artifacts for OSBS...")
        target_dir = os.path.join(self.target, "image")
        fetch_artifacts_url: List[Dict[str, str]] = []
        fetch_artifacts_pnc = OrderedDict()
        file_comments: Dict[str, str] = {}

        fetch_domains = config.get("common", "fetch_artifact_domains")

        for image in self.images:
            for artifact in image.all_artifacts:
                logger.info(
                    "Preparing artifact '{}' (of type {})".format(
                        artifact["name"], type(artifact)
                    )
                )

                # We only want to use fetch-artifact-url if
                # 1. is type _UrlResource
                # 2. if fetch_artifact_domains configured, URL conforms to that.
                process_fetch = False
                if isinstance(artifact, _UrlResource):
                    if fetch_domains is not None:
                        fad = fetch_domains.replace(" ", "").split(",")
                        # Verify if the URL can be used in fetch-artifact-url or now
                        for d in fad:
                            u = urlparse(d)
                            logger.debug(
                                "Parsed URL '{}' and path '{}'".format(u.netloc, u.path)
                            )
                            if u.netloc + u.path in artifact["url"]:
                                process_fetch = True
                        if not process_fetch:
                            artifact["lookaside"] = True
                            logger.warning(
                                "Ignoring {} as restricted to {}".format(
                                    artifact["url"], fad
                                )
                            )
                    else:
                        # Just process all UrlResource
                        process_fetch = True

                if process_fetch:
                    intersected_hash = [
                        x for x in crypto.SUPPORTED_HASH_ALGORITHMS if x in artifact
                    ]
                    logger.debug(
                        "Found checksum markers of {}".format(intersected_hash)
                    )
                    if not intersected_hash:
                        logger.warning(
                            "No checksum supplied for {}, calculating from the remote artifact".format(
                                artifact["url"]
                            )
                        )
                        intersected_hash = ["md5"]
                        tmpfile = tempfile.NamedTemporaryFile()
                        try:
                            artifact.download_file(artifact["url"], tmpfile.name)
                            artifact["md5"] = crypto.get_sum(tmpfile.name, "md5")
                        finally:
                            tmpfile.close()

                    fetch_artifacts_url.append(
                        {
                            "url": artifact["url"],
                            "target": os.path.join(artifact["target"]),
                        }
                    )
                    for c in intersected_hash:
                        fetch_artifacts_url[len(fetch_artifacts_url) - 1].update(
                            {c: artifact[c]}
                        )
                    patch_source_url(artifact, fetch_artifacts_url)
                    if "description" in artifact:
                        file_comments[artifact["url"]] = artifact["description"]
                    logger.debug(
                        "Artifact '{}' (as URL) added to fetch-artifacts-url.yaml with contents {}".format(
                            artifact["target"],
                            fetch_artifacts_url[len(fetch_artifacts_url) - 1],
                        )
                    )
                    # OSBS by default downloads all artifacts to artifacts/<target_path>
                    artifact["target"] = os.path.join("artifacts", artifact["target"])
                elif isinstance(artifact, _PlainResource) and config.get(
                    "common", "redhat"
                ):
                    try:
                        if "md5" not in artifact:
                            logger.error(
                                "Unable to use Brew as artifact does not have md5 checksum defined"
                            )
                            raise CekitError(
                                "Unable to use Brew as artifact does not have md5 checksum defined"
                            )
                        fetch_artifacts_url.append(
                            {
                                "md5": artifact["md5"],
                                "url": get_brew_url(artifact["md5"]),
                                "target": os.path.join(artifact["target"]),
                            }
                        )
                        patch_source_url(artifact, fetch_artifacts_url)

                        logger.debug(
                            "Artifact '{}' (as plain) added to fetch-artifacts-url.yaml".format(
                                artifact["target"]
                            )
                        )
                        # OSBS by default downloads all artifacts to artifacts/<target_path>
                        artifact["target"] = os.path.join(
                            "artifacts", artifact["target"]
                        )
                    except Exception:
                        logger.warning(
                            "Plain artifact {} could not be found in Brew, trying to handle it using lookaside cache".format(
                                artifact["name"]
                            )
                        )
                        artifact.copy(target_dir)
                        # TODO: This is ugly, rewrite this!
                        artifact["lookaside"] = True

                elif isinstance(artifact, _PncResource):
                    logger.info("Handling pnc resources for {}".format(artifact))
                    build = fetch_artifacts_pnc.setdefault(artifact["pnc_build_id"], [])
                    build.append(
                        {
                            "id": artifact["pnc_artifact_id"],
                            "target": artifact["target"],
                        }
                    )
                    # OSBS by default downloads all artifacts to artifacts/<target_path>
                    artifact["target"] = os.path.join("artifacts", artifact["target"])
                    if "url" in artifact:
                        file_comments[artifact["pnc_artifact_id"]] = artifact["url"]
                else:
                    logger.debug(
                        "Copying artifact {} to {}".format(artifact, target_dir)
                    )
                    artifact.copy(target_dir)

        if fetch_artifacts_pnc:
            fetch_artifacts_file = os.path.join(
                self.target, "image", "fetch-artifacts-pnc.yaml"
            )
            pnc = {
                "metadata": {"author": "CEKit " + version.__version__},
                "builds": [
                    {"build_id": key, "artifacts": fetch_artifacts_pnc.get(key)}
                    for key in fetch_artifacts_pnc
                ],
            }
            logger.debug("Writing {} to fetch-artifacts-pnc.yaml".format(pnc))
            with open(fetch_artifacts_file, "w") as _file:
                _file.write(
                    "# Created by CEKit version {}\n".format(version.__version__)
                )
                yaml.safe_dump(pnc, _file, default_flow_style=False, sort_keys=False)
            patch_file(file_comments, fetch_artifacts_file)
        if fetch_artifacts_url:
            fetch_artifacts_file = os.path.join(
                self.target, "image", "fetch-artifacts-url.yaml"
            )
            with open(fetch_artifacts_file, "w") as _file:
                _file.write(
                    "# Created by CEKit version {}\n".format(version.__version__)
                )
                yaml.safe_dump(
                    fetch_artifacts_url,
                    _file,
                    default_flow_style=False,
                    sort_keys=False,
                )
            patch_file(file_comments, fetch_artifacts_file)
        logger.debug("Artifacts handled")


# Used to modify either the fetch-artifact or fetch-pnc files to add extra human readable information.
def patch_file(file_comments: Dict[str, str], file: str) -> None:
    # Can't use it as a context manager with plain with as that is >= 3.2
    with closing(fileinput.input(file, inplace=True)) as input_list:
        for line in input_list:
            r = [
                line.replace("\n", " # " + value + "\n")
                for (key, value) in file_comments.items()
                if key in line
            ]
            if r:
                sys.stdout.write(r[0])
            else:
                sys.stdout.write(line)


def patch_source_url(
    artifact: Resource, fetch_artifacts_url: List[Dict[str, str]]
) -> None:
    if "source-url" in artifact:
        intersected_source_hash = [
            x for x in crypto.SUPPORTED_SOURCE_HASH_ALGORITHMS if x in artifact
        ]
        if not intersected_source_hash:
            raise CekitError(
                f"Unable to add source-url for artifact {artifact} as no checksum defined"
            )
        logger.debug(
            f"Found source-url {artifact['source-url']} and checksum markers of {intersected_source_hash}"
        )
        fetch_artifacts_url[len(fetch_artifacts_url) - 1].update(
            {"source-url": artifact["source-url"]}
        )
        for c in intersected_source_hash:
            fetch_artifacts_url[len(fetch_artifacts_url) - 1].update({c: artifact[c]})
