import os
import re
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
        parser.add_argument('--enable-dist-git', action='store_true', help='Enables dist-git plugin')
        return parser

    def __init__(self, dogen, args):
        super(DistGitPlugin, self).__init__(dogen, args)
        if  not self.args.enable_dist_git:
            return
        self.git = Git(self.log, os.path.dirname(self.descriptor), self.output)

    def prepare(self, cfg):
        if not self.args.enable_dist_git:
            return
        self.git.prepare()
        self.git.clean_scripts()

    def after_sources(self, files):
        if not self.args.enable_dist_git:
            return
        self.git.update_lookaside_cache(files)
        self.git.update()

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

    def __init__(self, log, source, path):
        self.log = log
        self.path = path
        self.dockerfile = os.path.join(self.path, "Dockerfile")

        self.name, self.branch, self.commit = Git.repo_info(path)
        self.source_repo_name, self.source_repo_branch, self.source_repo_commit = Git.repo_info(source)

    def prepare(self):
        self.log.debug("Resetting git repository...")

        # Reset all changes first - nothing should be done by hand
        with Chdir(self.path): 
            subprocess.check_output(["git", "reset", "--hard"])

        # Just check if the target branch is correct
        if not Tools.decision("You are currently working on the '%s' branch, is this what you want?" % self.branch):
            print("")
            self.switch_branch()

        self.old_version, self.old_release = self.read_version_and_release()

    def update(self):
        new_version, release = self.read_version_and_release()
        new_release = int(self.old_release) + 1

        self.log.info("New release will be: %s-%s." % (new_version, new_release))

        # Bump the release environment variable
        self.update_value("JBOSS_IMAGE_RELEASE", new_release)
        self.update_dist_git(new_version, new_release)

    def clean_scripts(self):
        """ Removes the scripts directory from staging and disk """
        shutil.rmtree(os.path.join(self.path, "scripts"), ignore_errors=True)

        with Chdir(self.path): 
            if os.path.exists("scripts"):
                self.log.info("Removing old scripts directory")
                subprocess.check_output(["git", "rm", "-rf", "scripts"])

    def read_dockerfile(self):
        with open(self.dockerfile, 'r') as f:
            return f.read()

    def read_value(self, dockerfile, exp):
        pattern = re.compile(exp)
        match = pattern.search(dockerfile)
        if match:
            return match.group(1)

        raise Exception("Could not find the '%s' pattern in %s" % (exp, dockerfile))

    def update_value(self, env, value):
        """
        This fnction updates the value of the selected environment variable
        or label that is set in the following pattern: env="[TO_REPLACE]".
        """

        # Read Dockerfile
        dockerfile = self.read_dockerfile()

        with open(self.dockerfile, 'w') as f:
            f.write(re.sub("(?<=%s=\")(.*)(?=\")" % env, str(value), dockerfile))

    def read_version_and_release(self):
        # If there is no Dockerfile, there are no old versions
        if not os.path.exists(self.dockerfile):
            return None, 0

        # Read *already existing* Dockerfile
        dockerfile = self.read_dockerfile()

        # Read envs from Dockerfile
        # Used to bump the release label and fill the commit message later
        try:
            version = self.read_value(dockerfile, 'JBOSS_IMAGE_VERSION="([\w\.]+)"')
        except:
            version = self.read_value(dockerfile, 'version="([\w\.]+)"')

        try:
            release = self.read_value(dockerfile, 'JBOSS_IMAGE_RELEASE="(\d+)"')
        except:
            try:
                release = self.read_value(dockerfile, 'release="(\d+)"')
            except:
                release = 0

        return version, release

    def switch_branch(self):

        with Chdir(self.path): 
            branches = subprocess.check_output(["git", "for-each-ref", "--format=%(refname)", "refs/heads"])

        branches = [b.strip().split("/")[-1] for b in branches.splitlines()] 
        
        self.log.info("Available branches:")

        for branch in branches:
            self.log.info(branch)

        target_branch = raw_input("\nTo which branch do you want to switch? ")

        if not target_branch in branches:
            print("")
            self.switch_branch()

        with Chdir(self.path): 
            # Checkout the correct branch
            self.log.info("Switching to '%s' branch" % target_branch)
            subprocess.check_output(["git", "checkout", "-q", "-f", target_branch])

    def update_lookaside_cache(self, files):
        if not files:
            return

        with Chdir(self.path):
            self.log.info("Updating lookaside cache...")
            subprocess.check_output(["rhpkg", "new-sources"] + files)
            self.log.info("Update finished.")

    def update_dist_git(self, version, release):
        with Chdir(self.path):
            # Add new Dockerfile
            subprocess.check_call(["git", "add", "Dockerfile"])

            # Add the scripts directory if it exists
            if os.path.exists(os.path.join(self.path, "scripts")):
                subprocess.check_call(["git", "add", "scripts"])

        commit_msg = "Sync"

        if self.source_repo_name:
            commit_msg += " with %s" % self.source_repo_name
 
        if self.source_repo_commit:
            commit_msg += ", commit %s" % self.source_repo_commit
 
        commit_msg += ", release %s-%s" % (version, release) 
 
        with Chdir(self.path): 
            # Commit the change 
            self.log.info("Commiting with message: '%s'" % commit_msg)
            subprocess.check_output(["git", "commit", "-m", commit_msg])

        
            untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"])

            if untracked: 
                self.log.warn("There are following untracked files: %s. Please review your commit." % ", ".join(untracked.splitlines()))
 
            diffs = subprocess.check_output(["git", "diff-files", "--name-only"])
 
            if diffs: 
                self.log.warn("There are uncommited changes in following files: '%s'. Please review your commit." % ", ".join(diffs.splitlines()))

        with Chdir(self.path): 
            subprocess.call(["git", "status"]) 
            subprocess.call(["read", "-p", "\nPress any key to see the last commit...", "-n1", "-s"]) 
            subprocess.call(["git", "show"]) 
 
        if Tools.decision("Do you want to review your changes?"): 
            with Chdir(self.path): 
                subprocess.call(["bash"]) 
 
        if Tools.decision("Do you want to push the commit?"): 
            print("")
            with Chdir(self.path): 
                self.log.info("Pushing change to the upstream repository...")
                subprocess.check_output(["git", "push", "-q"])
                self.log.info("Change pushed.")
 
                if Tools.decision("Do you want to execute a build on OSBS?"): 
                    subprocess.call(["rhpkg", "container-build"])

