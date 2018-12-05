import os
import getpass
import logging
import subprocess

from cekit.tools import Chdir
from cekit.errors import CekitError

logger = logging.getLogger('cekit')


class TestRunner(object):
    def __init__(self, target):
        """Check if behave and docker is installed properly"""
        self.target = os.path.abspath(target)
        try:
            # check that we have behave installed
            from behave.__main__ import main as behave_main
        except subprocess.CalledProcessError as ex:
            raise CekitError("Test Runner needs 'behave' installed, '%s'" %
                             ex.output)
        except Exception as ex:
            raise CekitError(
                "Test Runner needs behave installed!", ex)

    def run(self, image, run_tags, test_names):
        """Run test suite"""
        test_path = os.path.join(self.target, 'test')
        logger.debug("Running behave in '%s'." % test_path)
        args = [test_path,
                '--junit',
                '--junit-directory', 'results',
                '--no-skipped',
                '-t', '~ignore',
                '-D', 'IMAGE=%s' % image]

        if test_names:
            for name in test_names:
                args.append('--name')
                args.append("%s" % name)
        else:
            for tag in run_tags:
                if ':' in tag:
                    test_tag = tag.split(':')[0]

                args.append('-t')
                if '/' in tag:
                    args.append("@%s,@%s" % (test_tag.split('/')[0], test_tag))
                else:
                    args.append(tag)

            # Check if we're running runtests on CI or locally
            # If we run tests locally - skip all features that
            # are marked with the @ci annotation
            if getpass.getuser() != "jenkins":
                args.append("-t")
                args.append("~ci ")

        try:
            from behave.__main__ import main as behave_main

            with Chdir(os.path.join(self.target, 'test')):
                if behave_main(args) != 0:
                    raise CekitError("Test execution failed, please consult output above")
        except CekitError:
            raise
        except:
            raise CekitError("An error occurred while executing tests")
