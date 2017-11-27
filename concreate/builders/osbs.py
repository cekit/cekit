import logging
import os
import shutil
import subprocess
import sys

from builtins import input
from concreate.builder import Builder
from concreate.errors import ConcreateError

logger = logging.getLogger('concreate')


class OSBSBuilder(Builder):
    """Class representing OSBS builder."""

    def check_prerequisities(self):
        try:
            subprocess.check_output(
                ['rhpkg', 'help'], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as ex:
            raise ConcreateError("OSBS build engine needs 'rhpkg' tools installed, error: %s"
                                 % ex.output)
        except Exception as ex:
            raise ConcreateError(
                "OSBS build engine needs 'rhpkg' tools installed!", ex)

    def prepare(self, descriptor):
        """Prepares dist-git repository for OSBS build."""

        repository_key = descriptor.get('osbs', {}).get('repository', {})
        repository = repository_key.get('name')
        branch = repository_key.get('branch')

        if not (repository and branch):
            raise ConcreateError(
                "OSBS builder needs repostiory and branch provided!")

        self.dist_git_dir = os.path.join(os.path.expanduser('~/.concreate.d'),
                                         'osbs',
                                         repository)
        if not os.path.exists(os.path.dirname(self.dist_git_dir)):
            os.makedirs(os.path.dirname(self.dist_git_dir))

        self.dist_git = Git(self.dist_git_dir,
                            self.target,
                            repository,
                            branch)

        self.dist_git.prepare()
        self.dist_git.clean()

        self.artifacts = [a['name'] for a in descriptor.get('artifacts', [])]

        self.update_osbs_image_source()

    def update_osbs_image_source(self):
        with Chdir(os.path.join(self.target, 'image')):
            for obj in ["repos", "modules"]:
                if os.path.exists(obj):
                    shutil.copytree(obj, os.path.join(self.dist_git_dir, obj))
            shutil.copy("Dockerfile", os.path.join(
                self.dist_git_dir, "Dockerfile"))

        # Copy also every artifact
        for artifact in self.artifacts:
            shutil.copy(os.path.join(self.target,
                                     'image',
                                     artifact),
                        os.path.join(self.dist_git_dir,
                                     artifact))

    def update_lookaside_cache(self):
        logger.info("Updating lookaside cache...")
        if not self.artifacts:
            return
        cmd = ["rhpkg", "new-sources"] + self.artifacts
        logger.debug("Executing '%s'" % cmd)
        with Chdir(self.dist_git_dir):
            try:
                subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as ex:
                logger.error("Cannot run '%s', ouput: '%s'" % (cmd, ex.output))
                raise ConcreateError("Cannot update sources.")

        logger.info("Update finished.")

    def build(self, build_args):
        build_cmd = ["rhpkg", "container-build"]

        if not build_args.build_osbs_release:
            build_cmd.append("--scratch")

        with Chdir(self.dist_git_dir):
            self.dist_git.add()
            self.update_lookaside_cache()

            if self.dist_git.stage_modified():
                self.dist_git.commit()
                self.dist_git.push()
            else:
                logger.info("No changes made to the code, committing skipped")

            if decision("Do you want to build the image in OSBS?"):
                logger.info("Executing container build in OSBS...")

                logger.debug("Executing '%s'." % ' '.join(build_cmd))
                subprocess.check_call(build_cmd)


class Git(object):
    """Git support for osbs repositories"""
    @staticmethod
    def repo_info(path):

        with Chdir(path):
            if subprocess.check_output(["git", "rev-parse", "--is-inside-work-tree"]).strip().decode("utf8") != "true":
                raise Exception(
                    "Directory %s doesn't seem to be a git repository. Please make sure you specified correct path." % path)

            name = os.path.basename(subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"]).strip().decode("utf8"))
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip().decode("utf8")
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"]).strip().decode("utf8")

        return name, branch, commit

    def __init__(self, output, source, repo, branch, noninteractive=False):
        self.output = output
        self.repo = repo
        self.branch = branch
        self.dockerfile = os.path.join(self.output, "Dockerfile")
        self.noninteractive = noninteractive

        self.source_repo_name, self.source_repo_branch, self.source_repo_commit = Git.repo_info(
            source)

    def stage_modified(self):
        # Check if there are any files in stage (return code 1). If there are no files
        # (return code 0) it means that this is a rebuild, so skip committing
        if subprocess.call(["git", "diff-index", "--quiet", "--cached", "HEAD"]):
            return True

        return False

    def prepare(self):
        if os.path.exists(self.output):
            with Chdir(self.output):
                logger.info("Pulling latest changes in repo %s..." % self.repo)
                subprocess.check_output(["git", "fetch"])
                subprocess.check_output(
                    ["git", "checkout", "-f", self.branch], stderr=subprocess.STDOUT)
                subprocess.check_output(
                    ["git", "reset", "--hard", "origin/%s" % self.branch])
            logger.debug("Changes pulled")
        else:
            logger.info("Cloning %s git repository (%s branch)..." %
                        (self.repo, self.branch))
            subprocess.check_output(
                ["rhpkg", "-q", "clone", "-b", self.branch, self.repo, self.output])
            logger.debug("Repository %s cloned" % self.repo)

    def clean(self):
        """ Removes old generated scripts, repos and modules directories """
        with Chdir(self.output):
            git_files = subprocess.check_output(
                ["git", "ls-files", "."]).strip().decode("utf8").splitlines()
            for d in ["repos", "modules"]:
                logger.info("Removing old '%s' directory" % d)
                shutil.rmtree(d, ignore_errors=True)

                if d in git_files:
                    subprocess.check_output(["git", "rm", "-rf", d])

    def add(self):
        # Add new Dockerfile
        subprocess.check_call(["git", "add", "Dockerfile"])

        for d in ["repos", "modules"]:
            # we probably do not care about non existing files and other errors here
            subprocess.call(["git", "add", d])

    def commit(self):
        commit_msg = "Sync"

        if self.source_repo_name:
            commit_msg += " with %s" % self.source_repo_name

        if self.source_repo_commit:
            commit_msg += ", commit %s" % self.source_repo_commit

        # Commit the change
        logger.info("Commiting with message: '%s'" % commit_msg)
        subprocess.check_output(["git", "commit", "-q", "-m", commit_msg])

        untracked = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard"]).decode("utf8")

        if untracked:
            logger.warn("There are following untracked files: %s. Please review your commit." % ", ".join(
                untracked.splitlines()))

        diffs = subprocess.check_output(["git", "diff-files", "--name-only"]).decode("utf8")

        if diffs:
            logger.warn("There are uncommited changes in following files: '%s'. Please review your commit." % ", ".join(
                diffs.splitlines()))

        if not self.noninteractive:
            subprocess.call(["git", "status"])
            subprocess.call(["git", "show"])

        if not (self.noninteractive or decision("Are you ok with the changes?")):
            logger.info("Executing bash in the repo directory. After fixing the issues, exit the shell and Concreate will continue.")
            subprocess.call(["bash"], env={"PS1": "concreate $ ",
                                           "TERM": os.getenv("TERM", "xterm"),
                                           "HOME": os.getenv("HOME", "")})

    def push(self):
        if self.noninteractive or decision("Do you want to push the commit?"):
            print("")
            logger.info("Pushing change to the upstream repository...")
            subprocess.check_output(["git", "push", "-q"])
            logger.info("Change pushed.")
        else:
            logger.info("Changes are not pushed, exiting")
            sys.exit(0)


def decision(question):
    if input("\n%s [Y/n] " % question) in ["", "y", "Y"]:
        return True
    return False


class Chdir(object):
    """ Context manager for changing the current working directory """

    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)
