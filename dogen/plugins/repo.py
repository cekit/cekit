import glob
import os
import shutil

from dogen.plugin import Plugin

class Repo(Plugin):
    @staticmethod
    def info():
        return "repo", "Support for custom repo files"

    @staticmethod
    def inject_args(parser):
        parser.add_argument('--repo-files-dir', help='Provides path to directory with *.repo files that should be used to install rpms')
        return parser

    def __init__(self, dogen, args):
        super(Repo, self).__init__(dogen, args)

        self.repo_dir = self.args.repo_files_dir
        self.repo_files = []

    def after_sources(self, files):
        if not self.repo_files:
            return

        target_repos_dir = os.path.join(self.output, "repos")

        if os.path.exists(target_repos_dir):
            shutil.rmtree(target_repos_dir)

        os.makedirs(target_repos_dir)

        self.log.info("Copying custom repo files from '%s' directory..." % self.repo_dir)

        for f in sorted(self.repo_files):
            self.log.debug("Copying %s repo file..." % os.path.basename(f))
            shutil.copy2(f, target_repos_dir)

        self.log.debug("Done.")

    def prepare(self, cfg):
        if not self.repo_dir:
            self.log.debug("No directory with YUM repo files specified, skipping repo plugin")
            return

        if 'packages' not in cfg and 'rpms' not in cfg:
            self.log.debug("There are no packages to install, no repository files will be added either")
            return

        if not os.path.isdir(self.repo_dir):
            raise Exception("Provided path to directory with repo files: '%s' does not exists or is not a directory" % self.repo_dir)

        self.repo_files = glob.glob(os.path.join(self.repo_dir, "*.repo"))

        if not self.repo_files:
            self.log.warn("No repo files found in the '%s' directory" % self.repo_dir)
            return

        self.cfg = cfg
        self.cfg['additional_repos'] = []

        for f in sorted(self.repo_files):
            self.cfg['additional_repos'].append(os.path.splitext(os.path.basename(f))[0])
