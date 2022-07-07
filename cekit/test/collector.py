import logging
import os
import shutil
import sys

from cekit.tools import run_wrapper

logger = logging.getLogger("cekit")


class BehaveTestCollector(object):
    def __init__(self, descriptor_dir, target_dir):
        self.collected = False
        self.descriptor_dir = os.path.abspath(descriptor_dir)
        self.target_dir = os.path.abspath(target_dir)
        self.test_dir = os.path.join(self.target_dir, "test")

        # remove old test so we can get fresh ones collected
        shutil.rmtree(self.test_dir, ignore_errors=True)
        os.makedirs(self.test_dir)

    def dependencies(self, params=None):
        deps = {}

        loader_file = os.path.join(self.test_dir, "loader.py")

        if os.path.exists(loader_file):
            try:
                sys.path.append(self.test_dir)
                from loader import StepsLoader

                sys.path.remove(self.test_dir)
                return StepsLoader.dependencies(params)
            except Exception as e:
                logger.warning(
                    "Fetching information about test dependencies failed, running tests may not be possible!"
                )
                logger.debug("Exception: {}".format(e))

        return deps

    def _fetch_steps(self, version, url):
        """Method fetches common steps"""
        logger.info("Fetching common steps from '{}'.".format(url))
        cmd = [
            "git",
            "clone",
            "--depth",
            "1",
            url,
            self.test_dir,
            "-b",
            "v%s" % version,
        ]
        run_wrapper(cmd, False, f"Could not fetch steps from {url}")

    def collect(self, version, url):
        # first clone common steps
        self._fetch_steps(version, url)
        # copy tests from repository root
        repos_dir = os.path.join(self.target_dir, "repo")
        if os.path.exists(repos_dir):
            for repo_dir in os.listdir(repos_dir):
                self._copy_tests(source=repos_dir, name=repo_dir)
        logger.debug("Collected tests from repositories roots")

        # copy tests from collected modules
        modules_dir = os.path.join(self.target_dir, "image", "modules")
        if os.path.exists(modules_dir):
            for module_dir in os.listdir(modules_dir):
                self._copy_tests(source=modules_dir, name=module_dir)
        logger.debug("Collected tests from modules")

        # copy tests from image repo
        self._copy_tests(self.descriptor_dir, "", "image")
        logger.debug("Collected tests from image")
        logger.info("Collecting finished!")

        return self.collected

    def _copy_tests(self, source, name, target_dir=""):
        for obj_name in ["steps", "features"]:
            obj_path = os.path.join(source, name, "tests", obj_name)

            if os.path.exists(obj_path):
                target = os.path.join(self.test_dir, obj_name, name, target_dir)
                logger.debug(
                    "Collecting tests from '{}' into '{}'".format(obj_path, target)
                )
                if obj_name == "features":
                    self.collected = True
                shutil.copytree(obj_path, target)
