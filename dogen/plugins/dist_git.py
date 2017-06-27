import os
import shutil
import subprocess
import yaml

from dogen.tools import Tools, Chdir
from dogen.plugin import Plugin

class DistGitPlugin(Plugin):
    @staticmethod
    def info():
        return "dist-git", "Support for dist-git repositories"

    @staticmethod
    def inject_args(parser):
        parser.add_argument('--dist-git-enable', action='store_true', help='Enables dist-git plugin')
        parser.add_argument('--dist-git-assume-yes', action='store_true', help='Skip interactive mode and answer all question with "yes"')
        return parser

    def __init__(self, dogen, args):
        super(DistGitPlugin, self).__init__(dogen, args)

        if  not self.args.dist_git_enable:
            return

        self.repo = None
        self.branch = None

    def prepare(self, cfg):
        if not self.args.dist_git_enable:
            return

        dist_git_cfg = cfg.get('dogen', {}).get('plugins', {}).get('dist_git', None)

        if dist_git_cfg:
            self.repo = dist_git_cfg.get('repo')
            self.branch = dist_git_cfg.get('branch')

        if not (self.repo and self.branch):
            raise Exception("Dit-git plugin was activated, but repository and branch was not correctly provided")

        self.git = Git(self.log, self.output, os.path.dirname(self.descriptor), self.repo, self.branch, self.args.dist_git_assume_yes)

        self.git.prepare()
        self.git.clean()

    def after_sources(self, files):
        if not self.args.dist_git_enable:
            return

        with Chdir(self.output):
            self.update_lookaside_cache(files)
            self.git.add()

            if self.git.stage_modified():
                self.git.commit()
                self.git.push()
            else:
                self.log.info("No changes made to the code, commiting skipped")

            self.build()

    def update_lookaside_cache(self, artifacts):
        if not artifacts:
            return

        self.log.info("Updating lookaside cache...")
        subprocess.check_output(["rhpkg", "new-sources"] + artifacts.keys())
        self.log.info("Update finished.")

    def build(self):
        if self.args.dist_git_assume_yes or Tools.decision("Do you want to execute a build on OSBS?"):
            self.log.info("Executing container build on OSBS...")
            subprocess.call(["rhpkg", "container-build"])

class Git(object):
    """
    Git support for target directories
    """
    @staticmethod
    def repo_info(path):

        with Chdir(path):
            if subprocess.check_output(["git", "rev-parse", "--is-inside-work-tree"]).strip() != "true":
                raise Exception("Directory %s doesn't seem to be a git repository. Please make sure you specified correct path." % path)

            name = os.path.basename(subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).strip())
            branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip()
            commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).strip()

        return name, branch, commit

    def __init__(self, log, output, source, repo, branch, noninteractive=False):
        self.log = log
        self.output = output
        self.repo = repo
        self.branch = branch
        self.dockerfile = os.path.join(self.output, "Dockerfile")
        self.noninteractive = noninteractive

        self.source_repo_name, self.source_repo_branch, self.source_repo_commit = Git.repo_info(source)

    def stage_modified(self):
        # Check if there are any files in stage (return code 1). If there are no files
        # (return code 0) it means that this is a rebuild, so skip commiting
        if subprocess.call(["git", "diff-index", "--quiet", "--cached", "HEAD"]):
            return True

        return False

    def prepare(self):
        if os.path.exists(self.output):
            with Chdir(self.output):
                self.log.info("Pulling latest changes in repo %s..." % self.repo)
                subprocess.check_output(["git", "fetch"])
                subprocess.check_output(["git", "reset", "--hard", "origin/%s" % self.branch])
            self.log.debug("Changes pulled")
        else:
            self.log.info("Cloning %s git repository (%s branch)..." % (self.repo, self.branch))
            subprocess.check_output(["rhpkg", "-q", "clone", "-b", self.branch, self.repo, self.output])
            self.log.debug("Repository %s cloned" % self.repo)

    def clean(self):
        """ Removes old generated scripts """
        with Chdir(self.output):
            shutil.rmtree(os.path.join(self.output, "scripts"), ignore_errors=True)
            shutil.rmtree(os.path.join(self.output, "repos"), ignore_errors=True)

            for d in ["scripts", "repos"]:
                if os.path.exists(d):
                    self.log.info("Removing old '%s' directory" % d)
                    subprocess.check_output(["git", "rm", "-rf", d])

    def add(self):
        # Add new Dockerfile
        subprocess.check_call(["git", "add", "Dockerfile"])

        for d in ["scripts", "repos"]:
            if os.path.exists(os.path.join(self.output, d)):
                subprocess.check_call(["git", "add", d])

    def commit(self):
        commit_msg = "Sync"

        if self.source_repo_name:
            commit_msg += " with %s" % self.source_repo_name

        if self.source_repo_commit:
            commit_msg += ", commit %s" % self.source_repo_commit

        # Commit the change
        self.log.info("Commiting with message: '%s'" % commit_msg)
        subprocess.check_output(["git", "commit", "-q", "-m", commit_msg])

        untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"])

        if untracked:
            self.log.warn("There are following untracked files: %s. Please review your commit." % ", ".join(untracked.splitlines()))

        diffs = subprocess.check_output(["git", "diff-files", "--name-only"])

        if diffs:
            self.log.warn("There are uncommited changes in following files: '%s'. Please review your commit." % ", ".join(diffs.splitlines()))

        if not self.noninteractive:
            subprocess.call(["git", "status"])
            subprocess.call(["git", "show"])

        if not (self.noninteractive or Tools.decision("Are you ok with the changes?")):
            subprocess.call(["bash"])

    def push(self):
        if self.noninteractive or Tools.decision("Do you want to push the commit?"):
            print("")
            self.log.info("Pushing change to the upstream repository...")
            subprocess.check_output(["git", "push", "-q"])
            self.log.info("Change pushed.")
