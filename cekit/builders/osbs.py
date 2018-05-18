import logging
import os
import shutil
import subprocess
import sys

from cekit import tools
from cekit.builder import Builder
from cekit.errors import CekitError

logger = logging.getLogger('cekit')


class OSBSBuilder(Builder):
    """Class representing OSBS builder."""

    def __init__(self, build_engine, target, params={}):
        self._user = params.get('user')
        self._nowait = params.get('nowait', False)
        self._release = params.get('release', False)
        self._target = params.get('target')

        self._stage = params.get('stage', False)

        if params.get('redhat'):
            if params.get('stage'):
                self._rhpkg = 'rhpkg-stage'
            else:
                self._rhpkg = 'rhpkg'
        else:
            self._rhpkg = 'fedpkg'

        super(OSBSBuilder, self).__init__(build_engine, target, params={})

    def check_prerequisities(self):
        try:
            subprocess.check_output(
                [self._rhpkg, 'help'], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as ex:
            raise CekitError("OSBS build engine needs 'rhpkg' tools installed, error: %s"
                             % ex.output)
        except Exception as ex:
            raise CekitError(
                "OSBS build engine needs '%s' tools installed!" % self._rhpkg, ex)

    def prepare(self, descriptor):
        """Prepares dist-git repository for OSBS build."""

        repository_key = descriptor.get('osbs', {}).get('repository', {})
        repository = repository_key.get('name')
        branch = repository_key.get('branch')

        if not (repository and branch):
            raise CekitError(
                "OSBS builder needs repostiory and branch provided!")

        if self._stage:
            osbs_dir = 'osbs-stage'
        else:
            osbs_dir = 'osbs'

        self.dist_git_dir = os.path.join(os.path.expanduser(tools.cfg['common']['work_dir']),
                                         osbs_dir,
                                         repository)
        if not os.path.exists(os.path.dirname(self.dist_git_dir)):
            os.makedirs(os.path.dirname(self.dist_git_dir))

        self.dist_git = DistGit(self.dist_git_dir,
                                self.target,
                                repository,
                                branch)

        self.dist_git.prepare(self._stage, self._user)
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
            if os.path.exists("container.yaml"):
                shutil.copy("container.yaml", os.path.join(
                    self.dist_git_dir, "container.yaml"))
            if os.path.exists("content_sets.yml"):
                shutil.copy("content_sets.yml", os.path.join(
                    self.dist_git_dir, "content_sets.yml"))

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
        cmd = [self._rhpkg]
        if self._user:
            cmd += ['--user', self._user]
        cmd += ["new-sources"] + self.artifacts

        logger.debug("Executing '%s'" % cmd)
        with Chdir(self.dist_git_dir):
            try:
                subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as ex:
                logger.error("Cannot run '%s', ouput: '%s'" % (cmd, ex.output))
                raise CekitError("Cannot update sources.")

        logger.info("Update finished.")

    def build(self):
        cmd = [self._rhpkg]

        if self._user:
            cmd += ['--user', self._user]
        cmd.append("container-build")

        if self._target:
            cmd += ['--target', self._target]

        if self._nowait:
            cmd += ['--nowait']

        if not self._release:
            cmd.append("--scratch")

        with Chdir(self.dist_git_dir):
            self.dist_git.add()
            self.update_lookaside_cache()

            if self.dist_git.stage_modified():
                self.dist_git.commit()
                self.dist_git.push()
            else:
                logger.info("No changes made to the code, committing skipped")

            if tools.decision("Do you want to build the image in OSBS?"):
                build_type = "release" if self._release else "scratch"
                logger.info("Executing %s container build in OSBS..." % build_type)

                logger.debug("Executing '%s'." % ' '.join(cmd))
                subprocess.check_call(cmd)


class DistGit(object):
    """Git support for osbs repositories"""
    @staticmethod
    def repo_info(path):

        with Chdir(path):
            if subprocess.check_output(["git", "rev-parse", "--is-inside-work-tree"]) \
                    .strip().decode("utf8") != "true":

                raise Exception("Directory %s doesn't seem to be a git repository. "
                                "Please make sure you specified correct path." % path)

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

        self.source_repo_name, self.source_repo_branch, self.source_repo_commit = DistGit.repo_info(
            source)

    def stage_modified(self):
        # Check if there are any files in stage (return code 1). If there are no files
        # (return code 0) it means that this is a rebuild, so skip committing
        if subprocess.call(["git", "diff-index", "--quiet", "--cached", "HEAD"]):
            return True

        return False

    def prepare(self, stage, user=None):
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

            if stage:
                cmd = ['rhpkg-stage']
            else:
                cmd = ['rhpkg']

            if user:
                cmd += ['--user', user]
            cmd += ["-q", "clone", "-b", self.branch, self.repo, self.output]
            logger.debug("Cloning: '%s'" % ' '.join(cmd))
            subprocess.check_output(cmd)
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
        if os.path.exists("container.yaml"):
            subprocess.check_call(["git", "add", "container.yaml"])
        if os.path.exists("content_sets.yml"):
            subprocess.check_call(["git", "add", "content_sets.yml"])

        for d in ["repos", "modules"]:
            # we probably do not care about non existing files and other errors here
            subprocess.call(["git", "add", "--all", d])

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
            logger.warn("There are following untracked files: %s. Please review your commit."
                        % ", ".join(untracked.splitlines()))

        diffs = subprocess.check_output(["git", "diff-files", "--name-only"]).decode("utf8")

        if diffs:
            logger.warn("There are uncommited changes in following files: '%s'. "
                        "Please review your commit."
                        % ", ".join(diffs.splitlines()))

        if not self.noninteractive:
            subprocess.call(["git", "status"])
            subprocess.call(["git", "show"])

        if not (self.noninteractive or tools.decision("Are you ok with the changes?")):
            logger.info("Executing bash in the repo directory. "
                        "After fixing the issues, exit the shell and Cekit will continue.")
            subprocess.call(["bash"], env={"PS1": "cekit $ ",
                                           "TERM": os.getenv("TERM", "xterm"),
                                           "HOME": os.getenv("HOME", "")})

    def push(self):
        if self.noninteractive or tools.decision("Do you want to push the commit?"):
            print("")
            logger.info("Pushing change to the upstream repository...")
            cmd = ["git", "push", "-q", "origin", self.branch]
            logger.debug("Running command '%s'" % ' '.join(cmd))
            subprocess.check_output(cmd)
            logger.info("Change pushed.")
        else:
            logger.info("Changes are not pushed, exiting")
            sys.exit(0)


class Chdir(object):
    """ Context manager for changing the current working directory """

    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)
