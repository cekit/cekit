import os
import shutil
import subprocess

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
        self.git = Git(self.log, os.path.dirname(self.descriptor), self.output, self.args.dist_git_assume_yes)

    def prepare(self, cfg):
        if not self.args.dist_git_enable:
            return

        with Chdir(self.output):
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

    def __init__(self, log, source, path, noninteractive=False):
        self.log = log
        self.path = path
        self.dockerfile = os.path.join(self.path, "Dockerfile")
        self.noninteractive = noninteractive

        self.name, self.branch, _ = Git.repo_info(path)
        self.source_repo_name, self.source_repo_branch, self.source_repo_commit = Git.repo_info(source)

    def stage_modified(self):
        # Check if there are any files in stage (return code 1). If there are no files
        # (return code 0) it means that this is a rebuild, so skip commiting
        if subprocess.call(["git", "diff-index", "--quiet", "--cached", "HEAD"]):
            return True

        return False

    def prepare(self):
        self.log.debug("Resetting git repository...")

        # Reset all changes first - nothing should be done by hand
        subprocess.check_output(["git", "reset", "--hard"])

        # Just check if the target branch is correct
        if not Tools.decision("You are currently working on the '%s' branch, is this what you want?" % self.branch):
            print("")
            self.switch_branch()

    def clean(self):
        """ Removes old generated scripts """
        shutil.rmtree(os.path.join(self.path, "scripts"), ignore_errors=True)
        shutil.rmtree(os.path.join(self.path, "repos"), ignore_errors=True)

        for d in ["scripts", "repos"]:
            if os.path.exists(d):
                self.log.info("Removing old '%s' directory" % d)
                subprocess.check_output(["git", "rm", "-rf", d])

    def switch_branch(self):
        branches = subprocess.check_output(["git", "for-each-ref", "--format=%(refname)", "refs/heads"])
        branches = [b.strip().split("/")[-1] for b in branches.splitlines()]

        self.log.info("Available branches:")

        for branch in branches:
            self.log.info(branch)

        target_branch = raw_input("\nTo which branch do you want to switch? ")

        if not target_branch in branches:
            print("")
            self.switch_branch()

        # Checkout the correct branch
        self.log.info("Switching to '%s' branch" % target_branch)
        subprocess.check_output(["git", "checkout", "-q", "-f", target_branch])

    def add(self):
        # Add new Dockerfile
        subprocess.check_call(["git", "add", "Dockerfile"])

        for d in ["scripts", "repos"]:
            if os.path.exists(os.path.join(self.path, d)):
                subprocess.check_call(["git", "add", d])

    def commit(self):
        commit_msg = "Sync"

        if self.source_repo_name:
            commit_msg += " with %s" % self.source_repo_name

        if self.source_repo_commit:
            commit_msg += ", commit %s" % self.source_repo_commit

        # Commit the change
        self.log.info("Commiting with message: '%s'" % commit_msg)
        subprocess.check_output(["git", "commit", "-m", commit_msg])

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
