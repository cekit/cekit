import os
import logging
import shutil
import subprocess


logger = logging.getLogger('concreate')


class TestCollector(object):
    def __init__(self, descriptor_dir, target_dir):
        self.descriptor_dir = os.path.abspath(descriptor_dir)
        self.target_dir = os.path.abspath(target_dir)
        self.test_dir = os.path.join(self.target_dir, 'test')

        # remove old test so we can get fresh ones collected
        shutil.rmtree(self.test_dir, ignore_errors=True)
        os.makedirs(self.test_dir)

    def fetch_steps(self, version):
        """Methods fetches builtin steps """
        logger.info("Fetching common steps from 'https://github.com/jboss-openshift/concreate-test-steps'.")
        cmd = ['git',
               'clone',
               '--depth',
               '1',
               'https://github.com/jboss-openshift/concreate-test-steps',
               self.test_dir,
               '-b',
               'v%s' % version]
        logger.debug("Running '%s'" % ' '.join(cmd))
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)

    def collect(self, version):
        # first clone common steps
        self.fetch_steps(version)
        # copy tests from repository root
        tests_root = os.path.join(self.target_dir, 'repo')
        for tests_dir in os.listdir(tests_root):
            self._copy_tests(tests_root, tests_dir)
        logger.debug("Collected tests from repositories roots")

        # copy tests from collected modules
        tests_dirs = os.path.join(self.target_dir, 'image', 'modules')
        for tests_dir in os.listdir(tests_dirs):
            self._copy_tests(os.path.abspath(tests_dir), tests_dir)
        logger.debug("Collected tests from modules")

        # copy tests from image repo
        self._copy_tests(self.descriptor_dir, '')
        logger.debug("Collected tests from image")
        logger.info("Tests collected!")

    def _copy_tests(self, source, name):
        for obj_name in ['steps', 'features']:
            obj_path = os.path.join(source, name, 'tests', obj_name)
            if os.path.exists(obj_path):
                target = os.path.join(self.test_dir,
                                      obj_name,
                                      name)
                logger.debug("Collecting tests from '%s' into '%s'" % (obj_path,
                                                                       target))
                shutil.copytree(obj_path, target)
