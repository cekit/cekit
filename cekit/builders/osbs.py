import json
import logging
import os
import pathlib
import shutil
import subprocess
import sys
import time
from typing import TYPE_CHECKING, List, Optional, Tuple
from urllib.parse import urlparse

from jinja2 import Template

from cekit import tools
from cekit.builder import Builder
from cekit.cekit_types import DependencyDefinition, PathType
from cekit.config import Config
from cekit.tools.git import Git
from cekit.descriptor.resource import (
    Resource,
    _ImageContentResource,
    _PlainResource,
    _PncResource,
    _UrlResource,
)
from cekit.errors import CekitError
from cekit.tools import Chdir, copy_recursively, parse_env_timeout, run_wrapper

if TYPE_CHECKING:
    from cekit.descriptor.osbs import Repository

LOGGER = logging.getLogger("cekit")
CONFIG = Config()


class OSBSBuilder(Builder):
    """Class representing OSBS builder."""

    def __init__(self, params):
        super(OSBSBuilder, self).__init__("osbs", params)

        self._rhpkg_set_url_repos: List[str] = []
        self.artifacts: List[str] = []
        self.git: Git
        self.dist_git_dir: pathlib.Path

        if CONFIG.get("common", "redhat"):
            if self.params.get("stage"):
                self._fedpkg = "rhpkg-stage"
                self._koji = "brew-stage"
                self._koji_url = "https://brewweb.stage.engineering.redhat.com/brew"
            else:
                self._fedpkg = "rhpkg"
                self._koji = "brew"
                self._koji_url = "https://brewweb.engineering.redhat.com/brew"
        else:
            self._fedpkg = "fedpkg"
            self._koji = "koji"
            self._koji_url = "https://koji.fedoraproject.org/koji"

    @staticmethod
    def dependencies(params=None) -> DependencyDefinition:
        deps = {}

        if CONFIG.get("common", "redhat"):
            if params.get("stage"):
                fedpkg = "rhpkg-stage"
                koji = "brewkoji-stage"
                koji_executable = "brew-stage"
            else:
                fedpkg = "rhpkg"
                koji = "brewkoji"
                koji_executable = "brew"
        else:
            fedpkg = "fedpkg"
            koji = "koji"
            koji_executable = "koji"

        deps[fedpkg] = {"package": fedpkg, "executable": fedpkg}

        deps[koji] = {"package": koji, "executable": koji_executable}

        return deps

    def before_build(self) -> None:
        """Prepares dist-git repository for OSBS build."""

        super(OSBSBuilder, self).before_build()

        self._prepare_dist_git()
        self._copy_to_dist_git()
        self._sync_with_dist_git()

    def _prepare_dist_git(self):
        # TODO: Replace with actual type-safe getters.
        repository_key: "Repository" = self.generator.image.get("osbs", {}).get(
            "repository", {}
        )
        repository: str = repository_key.get("name")
        branch: str = repository_key.get("branch")

        if not (repository and branch):
            raise CekitError(
                "OSBS builder needs repository and branch provided, see https://docs.cekit.io/en/latest/descriptor/image.html#osbs for more information"
            )

        if self.params.stage:
            osbs_dir = "osbs-stage"
        else:
            osbs_dir = "osbs"

        # We need to prepare a list of all artifacts in every image (in case
        # of multi-stage builds) and in every module.
        all_artifacts: List[Resource] = []

        for image in self.generator.images:
            all_artifacts += image.all_artifacts

        # First get all artifacts that are not plain/url artifacts (the latter is added to fetch-artifacts.yaml)
        self.artifacts: List[str] = [
            a.target
            for a in all_artifacts
            if not isinstance(
                a, (_PncResource, _UrlResource, _PlainResource, _ImageContentResource)
            )
        ]
        # When plain artifact was handled using lookaside cache, we need to add it too
        self.artifacts += [
            a.target
            for a in all_artifacts
            if isinstance(a, _PlainResource) and a.get("lookaside")
        ]
        # Handle lookaside cache for URL based artifacts as well. This may happen if artifacts have been constrained
        # by fetch_artifact_domains
        self.artifacts += [
            a.target
            for a in all_artifacts
            if isinstance(a, _UrlResource) and a.get("lookaside")
        ]

        if (
            "packages" in self.generator.image
            and "set_url" in self.generator.image["packages"]
        ):
            self._rhpkg_set_url_repos = [
                x["url"]["repository"]
                for x in self.generator.image["packages"]["set_url"]
            ]

        self.dist_git_dir: PathType = os.path.join(
            os.path.expanduser(CONFIG.get("common", "work_dir")), osbs_dir, repository
        )
        if not os.path.exists(os.path.dirname(self.dist_git_dir)):
            os.makedirs(os.path.dirname(self.dist_git_dir))

        LOGGER.debug(f"Using dist-git directory of {self.dist_git_dir}")

        self.git = Git(
            self.dist_git_dir,
            self.target,
            repository,
            branch,
            # TODO: default result, dict, doesn't have attribute `extra_dir`
            self.generator.image.get("osbs", {}).extra_dir,
            self.params.assume_yes,
        )

        self.git.prepare(self.params.stage, self.params.user)
        self.git.clean(self.artifacts)

    def _copy_to_dist_git(self):
        LOGGER.debug(f"Copying files to dist-git '{self.dist_git_dir}' directory")
        copy_recursively(os.path.join(self.target, "image"), self.dist_git_dir)

    def _sync_with_dist_git(self):
        with Chdir(self.dist_git_dir):
            self.git.add(self.artifacts)
            self.update_lookaside_cache()

            if self.git.stage_modified():
                self.git.commit(self.params.commit_message)
                self.git.push()
            else:
                LOGGER.info("No changes made to the code, committing skipped")

    def _wait_for_osbs_task(self, task_id: str, timeout: int, current_time: int = 0):
        """Default timeout is 2hrs"""

        LOGGER.debug(f"Checking if task {task_id} is finished...")

        # Time between subsequent querying the API
        sleep_time = 20

        if current_time > timeout:
            raise CekitError(
                "Timed out while waiting for the task {} to finish, please check the task logs!".format(
                    task_id
                )
            )

        # Definition of task states
        states = {
            "free": 0,
            "open": 1,
            "closed": 2,
            "cancelled": 3,
            "assigned": 4,
            "failed": 5,
        }

        # Get information about the task
        result = run_wrapper(
            [self._koji, "call", "--json-output", "getTaskInfo", task_id],
            True,
            f"Could not check the task {task_id} result",
        )

        # Parse the returned JSON
        info = json.loads(result.stdout)

        # Task is closed which means that it was successfully finished
        if info["state"] == states["closed"]:
            return True

        # Task is in progress
        if (
            info["state"] == states["free"]
            or info["state"] == states["open"]
            or info["state"] == states["assigned"]
        ):
            # It's not necessary to query the API so often
            time.sleep(sleep_time)
            return self._wait_for_osbs_task(task_id, timeout, current_time + sleep_time)

        # In all other cases (failed, cancelled) task did not finish successfully
        raise CekitError(
            f"Task {task_id} did not finish successfully, please check the task logs!"
        )

    def update_lookaside_cache(self):
        LOGGER.info("Updating lookaside cache...")

        cache_artifacts = []
        for artifact in self.artifacts:
            # In case the artifact is a directory, we don't want to add it.
            # Instead, it will be staged.
            if os.path.isdir(artifact):
                continue

            cache_artifacts.append(artifact)

        if not cache_artifacts:
            return

        cmd = [self._fedpkg]
        if self.params.user:
            cmd += ["--user", self.params.user]
        if self.params.trace:
            cmd += ["--debug"]
        cmd += ["new-sources"] + cache_artifacts

        with Chdir(self.dist_git_dir):
            run_wrapper(cmd, False)

        LOGGER.info("Update finished.")

    def run(self):
        if self.params.sync_only:
            LOGGER.info(
                "The --sync-only parameter was specified, build will not be executed, exiting"
            )
            return

        build_id: str = ""
        git_tag: str = ""
        cmd: List[str] = [self._koji]

        if self.params.trace:
            cmd += ["--debug"]

        if self.params.user:
            cmd += ["--user", self.params.user]

        cmd += ["call", "--python", "buildContainer", "--kwargs"]

        with Chdir(self.dist_git_dir):
            # Get the url of the repository
            url = run_wrapper(
                ["git", "config", "--get", "remote.origin.url"], True
            ).stdout

            # Get the latest commit hash
            commit = run_wrapper(["git", "rev-parse", "HEAD"], True).stdout

            # Parse the dist-git repository url
            url = urlparse(url)
            # Construct the url again, with a hash and removed username and password, if any
            src = f"git+https://{url.hostname}/git{url.path}#{commit}"

            target = self.generator.image.get("osbs", {}).get("koji_target")

            # If target was not specified in the image descriptor
            if not target:
                # Default to computed target based on branch
                target = f"{self.git.branch}-containers-candidate"

            scratch = True

            if self.params.release:
                scratch = False

            kwargs = "{{'src': '{}', 'target': '{}', 'opts': {{'scratch': {}, 'git_branch': '{}', 'yum_repourls': {}}}}}".format(
                src, target, scratch, self.git.branch, self._rhpkg_set_url_repos
            )

            cmd.append(kwargs)

            LOGGER.info(f"About to execute '{' '.join(cmd)}'.")

            if self.params.assume_yes or tools.decision(
                "Do you want to build the image in OSBS?"
            ):
                build_type = "scratch" if scratch else "release"
                LOGGER.info(f"Executing {build_type} container build in OSBS...")

                task_id = run_wrapper(cmd, True).stdout

                LOGGER.info(
                    "Task {0} was submitted, you can watch the progress here: {1}/taskinfo?taskID={0}".format(
                        task_id, self._koji_url
                    )
                )

                if self.params.nowait:
                    return

                self._wait_for_osbs_task(
                    task_id, timeout=parse_env_timeout("OSBS_TIMEOUT", "7200")
                )

                LOGGER.info("Image was built successfully in OSBS!")

                if self.params.tag:
                    git_tag, build_id = self._establish_tag_name(task_id)
                    if git_tag:
                        self.git.tag(src, git_tag, build_id)
                        self.git.push(git_tag)
        if self.params.tag:
            # This is a bit of code reuse cheat - if tagging is enabled this will also tag
            # the image source repository (while the above block handles the dist-git source)
            url = run_wrapper(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                check=False,
            ).stdout
            if git_tag:
                self.git.tag(url, git_tag, build_id)
                self.git.push(git_tag)

    def _establish_tag_name(self, task_id: str) -> Tuple[str, str]:
        """This calls Brew to establish the NVR from the completed build in order to use that to tag the repositories

        :param task_id: A task_id to use to look up the NVR
        :returns a Tuple containing a tag and build_id. Maybe blank if the task was a scratch build.
        """
        tag: str = ""
        build_id: str = ""

        task_result = run_wrapper(
            # Don't need to handle raise_fault as OSBS build must have completed successfully to get to here.
            [self._koji, "call", "--json-output", "getTaskResult", task_id],
            True,
            f"Could not check the task {task_id} result",
        )

        koji_builds = json.loads(task_result.stdout)["koji_builds"]
        if koji_builds:
            build_id = koji_builds[0]
            build_result = run_wrapper(
                [self._koji, "call", "--json-output", "getBuild", build_id],
                True,
                f"Could not check the build {build_id} result",
            )
            nvr: str = json.loads(build_result.stdout)["nvr"]
            release: str = nvr.rpartition("-")[2]
            # The default rendered tag (name-version) with release equates to a NVR.
            tag: str = Template(self.params.tag).render(self.generator.image)
            if "/" in tag:
                LOGGER.debug(f"Replacing / in tag with - for {tag}")
                tag = tag.replace("/", "-")
            tag = tag + "-" + release
            LOGGER.info(f"Retrieved NVR {nvr} and generated {tag}")
        else:
            LOGGER.warning(
                f"No koji build found - maybe {task_id} was a scratch build?"
            )
        return tag, build_id
