import os
import sys
import logging
import shutil
import subprocess
import pkg_resources

from cekit.errors import CekitError
from pkg_resources import DistributionNotFound, VersionConflict

logger = logging.getLogger('cekit')


class TestCollector(object):
    collected = False
    test_dir = None

    def __init__(self, descriptor_dir, target_dir):
        self.descriptor_dir = os.path.abspath(descriptor_dir)
        self.target_dir = os.path.abspath(target_dir)
        self.test_dir = os.path.join(self.target_dir, 'test')

        # remove old test so we can get fresh ones collected
        shutil.rmtree(self.test_dir, ignore_errors=True)
        os.makedirs(self.test_dir)

    @staticmethod
    def dependencies():
        deps = {}

        if TestCollector.collected:
            loader_file = os.path.join(TestCollector.test_dir, "loader.py")

            if os.path.exists(loader_file):
                try:
                    sys.path.append(TestCollector.test_dir)
                    from loader import StepsLoader
                    sys.path.remove(TestCollector.test_dir)
                    return StepsLoader.dependencies()
                except Exception as e:
                    logger.warning(
                        "Fetching information about test dependencies failed, running tests may not be possible!")
                    logger.debug("Exception: {}".format(e))

        return deps

    def _fetch_steps(self, version, url):
        """ Method fetches common steps """
        logger.info("Fetching common steps from '%s'." % url)
        cmd = ['git',
               'clone',
               '--depth',
               '1',
               url,
               self.test_dir,
               '-b',
               'v%s' % version]
        logger.debug("Running '%s'" % ' '.join(cmd))
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)

    def collect(self, version, url):
        # first clone common steps
        self._fetch_steps(version, url)
        # copy tests from repository root
        tests_root = os.path.join(self.target_dir, 'repo')
        if os.path.exists(tests_root):
            for tests_dir in os.listdir(tests_root):
                self._copy_tests(tests_root, tests_dir)
        logger.debug("Collected tests from repositories roots")

        # copy tests from collected modules
        tests_dirs = os.path.join(self.target_dir, 'image', 'modules')
        if os.path.exists(tests_dirs):
            for tests_dir in os.listdir(tests_dirs):
                self._copy_tests(tests_dirs, tests_dir)
        logger.debug("Collected tests from modules")

        # copy tests from image repo
        self._copy_tests(self.descriptor_dir, '', 'image')
        logger.debug("Collected tests from image")
        logger.info("Tests collected!")

        return TestCollector.collected

    def _copy_tests(self, source, name, target_dir=''):
        for obj_name in ['steps', 'features']:
            obj_path = os.path.join(source, name, 'tests', obj_name)

            if os.path.exists(obj_path):
                target = os.path.join(self.test_dir,
                                      obj_name,
                                      name,
                                      target_dir)
                logger.debug("Collecting tests from '%s' into '%s'" % (obj_path,
                                                                       target))
                if obj_name == 'features':
                    TestCollector.collected = True
                    TestCollector.test_dir = self.test_dir
                shutil.copytree(obj_path, target)
