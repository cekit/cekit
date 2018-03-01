import os
import logging
import shutil
import subprocess
import pkg_resources

from cekit.errors import CekitError
from pkg_resources import DistributionNotFound, VersionConflict


logger = logging.getLogger('cekit')


class TestCollector(object):
    collected = False

    def __init__(self, descriptor_dir, target_dir):
        self.descriptor_dir = os.path.abspath(descriptor_dir)
        self.target_dir = os.path.abspath(target_dir)
        self.test_dir = os.path.join(self.target_dir, 'test')

        # remove old test so we can get fresh ones collected
        shutil.rmtree(self.test_dir, ignore_errors=True)
        os.makedirs(self.test_dir)

    def _requirement_available(self, req, silent=False):
        try:
            pkg_resources.require(req)
            return True
        except DistributionNotFound as e:
            if not silent:
                logger.error("Test steps require library '%s' that is not available." % req)
                self._suggest_package(req)
            return False
        except VersionConflict as e:
            logger.error("Test steps dependencies have version conflict; %s" % str(e))
            return False

    def _suggest_package(self, name):
        deps = {
            'docker': ['python-docker-py', 'python2-docker', 'python3-docker'],
            'behave': ['python2-behave', 'python3-behave'],
            'requests': ['python2-requests', 'python3-requests']
        }

        if name in deps:
            logger.error("Try to install %s RPM package using yum/dnf depending on what OS "
                         "are you and what Python version you use. You can also use Python "
                         "package manager of your choice to install '%s' library." %
                         (" or ".join(deps[name]), name))

    def _validate_steps_requirements(self):
        logger.debug("Validating steps requirements...")

        req_docker = self._requirement_available('docker', True)
        req_docker_py = self._requirement_available('docker-py', True)

        if not (req_docker or req_docker_py):
            self._suggest_package('docker')
            raise CekitError("Could not find Docker client library, see logs above")

        for req in ['behave', 'requests']:
            if not self._requirement_available(req):
                raise CekitError("Handling of test steps requirements "
                                     "failed, see log for more info.")

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
        self._validate_steps_requirements()
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
        return self.collected

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
                    self.collected = True
                shutil.copytree(obj_path, target)
