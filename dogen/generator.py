# -*- coding: utf-8 -*-

import argparse
import hashlib
import getpass
import os
import shutil
import sys
import urllib
import yaml
import subprocess
import git
import re

from jinja2 import FileSystemLoader, Environment

class Chdir(object):

    """ Context manager for changing the current working directory """

    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)

class TemplateHelper(object):
    def basename(self, url):
        """ Simple helper to return the file specified name """

        return os.path.basename(url)

    def cmd(self, arr):
        """
        Generates array of commands that could be used like this:
        CMD {{ helper.cmd(cmd) }}
        """

        ret = []
        for cmd in arr:
            ret.append("\"%s\"" % cmd)
        return "[%s]" % ', '.join(ret)

    def component(self, name):
        """
        Returns the vomponent name based on the image name
        """

        return "%s-docker" % name.replace("/", "-")

    def base_image(self, base_image, version):
        """
        Return the base image name that could be used in FROM
        instruction.
        """

        if ':' in base_image:
            return base_image
        else:
            return "%s:%s" % (base_image, version)

class Generator(object):
    def __init__(self, template, output, scripts=None, without_sources=False, dist_git=False):
        with open(template, 'r') as stream:
            self.cfg = yaml.safe_load(stream)

        self.input = os.path.realpath(os.path.dirname(os.path.realpath(template)))
        self.output = output
        self.scripts = scripts

        self.template = template
        self.pwd = os.path.realpath(os.path.dirname(os.path.realpath(__file__)))
        self.without_sources = without_sources
        self.dist_git = dist_git

        self.dockerfile = os.path.join(self.output, "Dockerfile")

        if self.dist_git:
            self.repo = self.init_repo(self.output)
            self.input_repo = self.init_repo(self.input)

    def init_repo(self, path):
        try:
            return git.Repo(path)
        except:
            raise Exception("Specified path (%s) is not a Git repository, aborting" % path)

    def switch_branch(self):
        print "Available branches:"
        for branch in self.repo.branches:
            print "  - %s" % branch

        target_branch = raw_input("To which branch do you want to switch? ")

        if not target_branch in [branch.name for branch in self.repo.branches]:
            self.switch_branch()

        # Change the reference to head to point to the new branch
        self.repo.head.reference = self.repo.branches[target_branch]

        # Reset the git repo to HEAD, so we can be sure to work on a clean state
        self.repo.head.reset(index=True, working_tree=True)

    def prepare_dist_git(self):
        # Reset all changes first - nothing should be done by hand
        self.repo.head.reset(index=True, working_tree=True)

        # Just check if the target branch is correct
        if not self.decision("You are currently working on the '%s' branch, is this what you want?" % self.repo.active_branch):
            self.switch_branch()

    def read_version_and_release(self):
        # If there is no Dockerfile, there are no old versions
        if not os.path.exists(self.dockerfile):
            return None, 0

        # Read *already existing* Dockerfile
        dockerfile = self.read_dockerfile()

        # Read envs from Dockerfile
        # Used to bump the release label and fill the commit message later
        try:
            version = self.read_value(dockerfile, 'JBOSS_IMAGE_VERSION="([\d\.]+)"')
        except:
            version = self.read_value(dockerfile, 'Version="([\d\.]+)"')

        try:
            release = self.read_value(dockerfile, 'JBOSS_IMAGE_RELEASE="(\d+)"')
        except:
            try:
                release = self.read_value(dockerfile, 'Release="(\d+)"')
            except:
                release = 0

        return version, release


    def update_dist_git(self, version, release):

        # Add new Docekrfile
        self.repo.index.add(["Dockerfile"])

        # Add the scripts directory if it exists
        if self.scripts:
            self.repo.index.add(["scripts"])

        # Commit the change
        self.repo.index.commit("Sync with jboss-dockerfiles, commit %s, release %s-%s" % (self.input_repo.head.commit.hexsha, version, release))

        untracked = self.repo.untracked_files

        if untracked:
            print "There are following untracked files: %s. Please review your commit." % ", ".join(untracked)

        diffs = self.repo.index.diff(None)

        if diffs:
            print "There are uncommited changes. Please review your commit"

        if self.decision("Do you want to review your changes?"):
            with Chdir(self.output):
                subprocess.call(["bash"])

        if self.decision("Do you want to push the commit?"):
            self.repo.remotes.origin.push()

            if self.decision("Do you want to execute a build on OSBS?"):
                with Chdir(self.output):
                    subprocess.call(["rhpkg", "container-build"])

    def run(self):
        if self.dist_git:
            self.prepare_dist_git()

            old_version, old_release = self.read_version_and_release()


        # Remove the scripts directory
        shutil.rmtree(os.path.join(self.output, "scripts"), ignore_errors=True)

        if self.dist_git:
            # Remove the scripts directory from index too
            for diff in self.repo.index.diff(None):
                self.repo.index.remove([diff.a_blob.path])

        if not os.path.exists(self.output):
            os.makedirs(self.output)
        try:
            for scripts in self.cfg['scripts']:
                package = scripts['package']
                output_path = os.path.join(self.output, "scripts", package)
                try:
                    # Poor-man's workaround for not copying multiple times the same thing
                    if not os.path.exists(output_path):
                        shutil.copytree(src=os.path.join(self.scripts, package), dst=output_path)
                        print("Package %s copied" % package)
                except Exception, ex:
                    print("Cannot copy package %s because: %s" % (package, str(ex)))
        except KeyError:
            pass

        self.render_from_template()
        self.handle_sources()

        if self.dist_git:

            new_version, release = self.read_version_and_release()
            new_release = int(old_release) + 1

            print "New release will be: %s-%s." % (new_version, new_release)

            # Bump the release environment variable
            self.update_value("JBOSS_IMAGE_RELEASE", new_release)

            self.update_dist_git(new_version, new_release)

    def decision(self, question):
        if raw_input("%s [Y/n] " % question) in ["", "y", "Y"]:
            return True

        return False

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

    def render_from_template(self):
        print("Rendering Dockerfile...")
        loader = FileSystemLoader(os.path.join(self.pwd, "templates"))
        env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
        env.globals['helper'] = TemplateHelper()
        template = env.get_template("template.jinja")

        with open(self.dockerfile, 'w') as f:
            f.write(template.render(self.cfg).encode('utf-8'))

    def handle_sources(self):
        if not 'sources' in self.cfg or self.without_sources:
            return

        files = []

        for source in self.cfg['sources']:
            url = source['url']
            basename = os.path.basename(url)
            files.append(basename)
            filename = ("%s/%s" %(self.output, basename))
            passed = False
            try:
                if os.path.exists(filename):
                    print("Checking %s hash" % filename)
                    self.check_sum(filename, source['hash'])
                    passed = True
            except:
                passed = False

            if not passed:
                if getpass.getuser() == 'jenkins':
                    url = "http://172.17.42.1/%s" % basename

                print("Downloading %s" % url)
                urllib.urlretrieve(url, filename)
                print("Checking %s hash" % filename)
                self.check_sum(filename, source['hash'])

        # If destination is a dist-git repository add the sources files
        # to lookaside cache
        if self.dist_git:
            with Chdir(self.output):
                subprocess.call(["rhpkg", "new-sources"] + files)

    def check_sum(self, filename, checksum):
         filesum = hashlib.md5(open(filename, 'rb').read()).hexdigest()
         if filesum != checksum:
             raise Exception("The md5sum computed for the '%s' file ('%s') doesn't match the '%s' value" % (filename, filesum, checksum))



