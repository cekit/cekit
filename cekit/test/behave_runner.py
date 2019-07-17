import getpass
import logging
import os

from cekit.errors import CekitError
from cekit.tools import Chdir

try:
    from behave.__main__ import main as behave_main
except ImportError:
    pass

logger = logging.getLogger('cekit')


class BehaveTestRunner(object):
    def __init__(self, target):
        self.target = os.path.abspath(target)

    @staticmethod
    def dependencies(params=None):
        deps = {}

        deps['python-behave'] = {
            'library': 'behave',
            'package': 'python2-behave',
            'fedora': {
                'package': 'python3-behave'}
        }

        return deps

    def run(self, image, run_tags, test_names):
        """Run test suite"""
        test_path = os.path.join(self.target, 'test')
        logger.debug("Running behave in '{}'.".format(test_path))
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
            with Chdir(os.path.join(self.target, 'test')):
                logger.debug("behave args: {}".format(args))
                if behave_main(args) != 0:
                    raise CekitError("Test execution failed, please consult output above")
        except CekitError:
            raise
        except:
            raise CekitError("An error occurred while executing tests")
