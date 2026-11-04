from typing import TYPE_CHECKING, List, Optional, Tuple
from cekit.cekit_types import DependencyDefinition, PathType
from cekit.errors import CekitError
from cekit.tools import Chdir, run_wrapper
import os
import logging
import shutil

LOGGER = logging.getLogger("cekit")

class Git(object):
    """
    Git tool wrapper.

    This started out as a copy of the same class from the OSBS builder
    but has diverged to support the Konflux builder.
    """

    @staticmethod
    def repo_info(path) -> Tuple[str, str, str]:
        with Chdir(path):
            if (
                run_wrapper(["git", "rev-parse", "--is-inside-work-tree"], True).stdout
                != "true"
            ):
                raise Exception(
                    "Directory {} doesn't seem to be a git repository. "
                    "Please make sure you specified correct path.".format(path)
                )

            name: str = os.path.basename(
                run_wrapper(["git", "rev-parse", "--show-toplevel"], True).stdout
            )
            branch: str = run_wrapper(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], True
            ).stdout
            commit: str = run_wrapper(["git", "rev-parse", "HEAD"], True).stdout

        return name, branch, commit

    def __init__(
        self,
        output: PathType,
        source: PathType,
        repo: str,
        branch: str,
        osbs_extra: PathType,
        noninteractive: bool = False,
    ):
        self.output: PathType = output
        self.source: PathType = source
        self.repo: str = repo
        self.branch: str = branch
        self.osbs_extra: PathType = osbs_extra
        self.noninteractive: bool = noninteractive

        (
            self.source_repo_name,
            self.source_repo_branch,
            self.source_repo_commit,
        ) = Git.repo_info(source)

    def stage_modified(self) -> bool:
        # Check if there are any files in stage (return code 1). If there are no files
        # (return code 0) it means that this is a rebuild, so skip committing
        if run_wrapper(
            ["git", "diff-index", "--quiet", "--cached", "HEAD"], False, check=False
        ).returncode:
            return True

        return False

    def prepare(self, stage, user: Optional[str] = None) -> None:
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
            LOGGER.info(f"Cloning {self.repo} git repository ({self.branch} branch)...")

            if stage:
                cmd = ["rhpkg-stage"]
            else:
                cmd = ["rhpkg"]

            if user:
                cmd += ["--user", user]
            cmd += ["-q", "clone", "-b", self.branch, self.repo, self.output]
            LOGGER.debug(f"Cloning: '{' '.join(cmd)}'")
            run_wrapper(cmd, False)
            LOGGER.debug(f"Repository {self.repo} cloned")

    def clean(self, artifacts: List[str]) -> None:
        """
        Removes old generated scripts, repos and modules directories
        as well as all directories that are defined as artifacts.
        """
        directory_artifacts = []

        for artifact in artifacts:
            if os.path.isdir(artifact):
                directory_artifacts.append(artifact)

        with Chdir(self.output):
            git_files = run_wrapper(["git", "ls-files", "."], True).stdout.splitlines()

            for d in ["repos", "modules"] + directory_artifacts:
                LOGGER.info(f"Removing old '{d}' directory")
                shutil.rmtree(d, ignore_errors=True)

                if d in git_files:
                    run_wrapper(["git", "rm", "-rf", d], False)

            if os.path.exists(self.osbs_extra):
                LOGGER.info(f"Removing old osbs extra directory : {self.osbs_extra}")
                run_wrapper(["git", "rm", "-rf", self.osbs_extra], False)

            if os.path.exists("fetch-artifacts-url.yaml"):
                LOGGER.info("Removing old 'fetch-artifacts-url.yaml' file")
                run_wrapper(["git", "rm", "-rf", "fetch-artifacts-url.yaml"], False)

            if os.path.exists("fetch-artifacts-pnc.yaml"):
                LOGGER.info("Removing old 'fetch-artifacts-pnc.yaml' file")
                run_wrapper(["git", "rm", "-rf", "fetch-artifacts-pnc.yaml"], False)

    def add(self, artifacts: List[str]) -> None:
        LOGGER.debug("Adding files to git...")

        for file in sorted(os.listdir(".")):
            if file == ".git":
                LOGGER.debug("Skipping '.git' directory")
                continue

            # If the artifact to add is a directory do not skip it
            if file in artifacts and not os.path.isdir(file):
                LOGGER.debug(
                    f"Skipping staging '{file}' in git because it is an artifact"
                )
                continue

            LOGGER.debug(f"Staging '{file}'...")
            run_wrapper(["git", "add", "--all", file], False)

    def commit(self, commit_msg: str) -> None:
        if not commit_msg:
            commit_msg = "Sync"

            if self.source_repo_name:
                commit_msg += f" with {self.source_repo_name}"

            if self.source_repo_commit:
                commit_msg += f", commit {self.source_repo_commit}"

        # Commit the change
        LOGGER.info(f"Committing with message: '{commit_msg}'")
        run_wrapper(["git", "commit", "-q", "-m", commit_msg], False)
        untracked = run_wrapper(
            ["git", "ls-files", "--others", "--exclude-standard"], True
        ).stdout
        if untracked:
            LOGGER.warning(
                "There are following untracked files: {}. Please review your commit.".format(
                    ", ".join(untracked.splitlines())
                )
            )

        diffs = run_wrapper(["git", "diff-files", "--name-only"], True).stdout
        if diffs:
            LOGGER.warning(
                "There are uncommitted changes in following files: '{}'. "
                "Please review your commit.".format(", ".join(diffs.splitlines()))
            )

        if not self.noninteractive:
            run_wrapper(["git", "status"], False)
            run_wrapper(["git", "show"], False)

        if not (self.noninteractive or tools.decision("Are you ok with the changes?")):
            LOGGER.info(
                "Executing bash in the repo directory. "
                "After fixing the issues, exit the shell and Cekit will continue."
            )
            subprocess.call(
                ["bash"],
                env={
                    "PS1": "cekit $ ",
                    "TERM": os.getenv("TERM", "xterm"),
                    "HOME": os.getenv("HOME", ""),
                },
            )

    def tag(self, url: str, tag: str, build_id) -> None:
        LOGGER.info(f"Tagging git repository ({url}) with {tag} from build {build_id}")
        # cgit requires annotated tags.
        run_wrapper(
            [
                "git",
                "tag",
                "-a",
                "-m",
                f"CEKit automated tag from build {build_id}",
                tag,
            ],
            False,
        )

    def push(self, tag: str = None) -> None:
        if self.noninteractive or tools.decision("Do you want to push the commit?"):
            print("")
            LOGGER.info("Pushing change to the upstream repository...")
            if tag:
                cmd = ["git", "push", "origin", tag]
            else:
                cmd = ["git", "push", "-q", "origin", self.branch]
            run_wrapper(cmd, False)
            LOGGER.info("Change pushed.")
        else:
            LOGGER.info("Changes are not pushed, exiting")
            sys.exit(0)
