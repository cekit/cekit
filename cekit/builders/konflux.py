from typing import TYPE_CHECKING, List, Optional, Tuple
import logging
import sys
import os
import pathlib
from cekit.builder import Builder
from cekit.tools.git import Git
from cekit.errors import CekitError
from cekit.config import Config
from cekit.cekit_types import PathType

from cekit.tools import Chdir, copy_recursively, run_wrapper

LOGGER = logging.getLogger("cekit")
CONFIG = Config()

class KonfluxBuilder(Builder):
    """Class representing Konflux builder."""


    def __init__(self, params):
        super(KonfluxBuilder, self).__init__("konflux", params)
        LOGGER.debug("KonfluxBuilder init")

        self.artifacts: List[str] = []
        self.repopath: pathlib.Path

    def run(self) -> None:
        """
        run is a no-op for the Konflux builder.
        """
        LOGGER.debug("KonfluxBuilder run")

    def before_build(self) -> None:
        """
        This is where the magic happens.
        """
        LOGGER.debug("KonfluxBuilder before_build")

        self._prepare_konflux_git()
        self._copy_to_git()
        self._sync_with_git()

    def _prepare_konflux_git(self) -> None:
        LOGGER.debug("KonfluxBuilder _prepare_konflux_git")

        repokey: "Repository" = self.generator.image.get("konflux", {}).get("repository",{})
        repo: str = repokey.get("uri")
        ref: str = repokey.get("ref")
        if not (repo and ref):
            raise CekitError("""
                Konflux Builder needs konflux.repository.uri and konflux.repository.ref defined."
            """)

        components = [ x.get('value',None) for x in self.generator.image.get("labels")
            if x.get('name','') == 'com.redhat.component' ]
        if len(components) < 1:
            raise CekitError("""
            Konflux Builder needs images to have the label com.redhat.component.
            """)
        dirname = components[0]
        if not dirname:
            raise CekitError("""
            Konflux Builder needs images to have the label com.redhat.component.
            """)

        self.repopath: PathType = os.path.join(
            os.path.expanduser(CONFIG.get("common", "work_dir")), "konflux", dirname
        )
        LOGGER.debug(f"KonfluxBuilder: Using git repo path of {self.repopath}")
        if not os.path.exists(os.path.dirname(self.repopath)):
            os.makedirs(os.path.dirname(self.repopath))

        self.git = KonfluxGit(
            self.repopath, # output
            self.target,   # source
            repo,          # repo
            ref,           # branch
            -1,            # HACK: osbs_extra. Path. -1 to get os.path.exists -> false
            True           # noninteractive
        )

        self.git.prepare(
            False, # stageself.params.stage, self.params.user)
            None,  # user (for rhpkg)
        )
        self.git.clean(self.artifacts)

    def _copy_to_git(self):
        LOGGER.debug(f"Copying files to dist-git '{self.repopath}' directory")
        copy_recursively(os.path.join(self.target, "image"), self.repopath)

    def _sync_with_git(self):
        with Chdir(self.repopath):
            self.git.add(self.artifacts)

            if self.git.stage_modified():
                self.git.commit(self.params.commit_message)
                #self.git.push()
            else:
                LOGGER.info("No changes made to the code, committing skipped")

class KonfluxGit(Git):
    """
    overloaded Git object, customized to the needs of the Konflux
    builder.
    """
    def __init__(
        self,
        output: PathType,
        source: PathType,
        repo: str,
        branch: str,
        osbs_extra: PathType,
        noninteractive: bool = False,
    ):
        super(KonfluxGit, self).__init__(
            output,
            source,
            repo,
            branch,
            osbs_extra,
            noninteractive,
        )

    def prepare(self, stage, user: Optional[str] = None) -> None:
        LOGGER.debug(f"KonfluxBuilder: KonfluxGit.prepare")

        if os.path.exists(self.output):
            with Chdir(self.output):
                LOGGER.info(f"Fetching latest changes in repo {self.repo}...")
                run_wrapper(["git", "fetch"], False)
                LOGGER.debug(f"Checking out {self.branch} branch...")
                run_wrapper(["git", "checkout", "-f", self.branch], False)
                LOGGER.debug("Resetting branch...")
                run_wrapper(["git", "reset", "--hard", f"origin/{self.branch}"], False)
                LOGGER.debug("Removing any untracked files or directories...")
                run_wrapper(["git", "clean", "-fdx"], False)
            LOGGER.debug("Changes pulled")
        else:
            LOGGER.info(f"Cloning {self.repo} git repository (ref {self.branch})...")

            cmd = ["git", "clone", "-b", self.branch, self.repo, self.output]
            LOGGER.debug(f"Cloning: '{' '.join(cmd)}'")
            run_wrapper(cmd, False)
            LOGGER.debug(f"Repository {self.repo} cloned")
