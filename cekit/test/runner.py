import os
import getpass
import logging
import subprocess


from cekit.errors import CekitError

logger = logging.getLogger('cekit')


class TestRunner(object):
    def __init__(self, target):
        """Check if behave and docker is installed properly"""
        self.target = os.path.abspath(target)
        try:
            subprocess.check_output(['behave', '--version'], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as ex:
            raise CekitError("Test Runner needs 'behave' installed, '%s'" %
                             ex.output)
        except Exception as ex:
            raise CekitError(
                "Test Runner needs behave installed!", ex)

    def run(self, image, run_tags):
        """Run test suite"""
        cmd = ['behave',
               '--junit',
               '--junit-directory', 'results',
               '-t', '~ignore',
               '--no-skipped',
               '-D', 'IMAGE=%s' % image]

        for tag in run_tags:
            if ':' in tag:
                test_tag = tag.split(':')[0]

            cmd.append('-t')
            if '/' in tag:
                cmd.append("@%s,@%s" % (test_tag.split('/')[0], test_tag))
            else:
                cmd.append(tag)

        # Check if we're running runtests on CI or locally
        # If we run tests locally - skip all features that
        # are marked with the @ci annotation
        if getpass.getuser() != "jenkins":
            cmd.append("-t")
            cmd.append("~ci ")

        logger.debug("Running '%s'" % ' '.join(cmd))
        try:
            subprocess.check_call(cmd,
                                  stderr=subprocess.STDOUT,
                                  cwd=os.path.join(self.target, 'test'))
        except:
            raise CekitError("Test execution failed, please consult output above")
