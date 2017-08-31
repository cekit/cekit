import argparse
import tempfile
import unittest
import mock
import os
import re
import shutil

from dogen.generator import Generator
from dogen.descriptor import Descriptor

basic_config = {'release': 1,
                'version': 1,
                'cmd': 'whoami',
                'from': 'scratch',
                'name': 'testimage'}

    # Generate a Dockerfile, and check what is in it.
class TestDockerfile(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.workdir = tempfile.mkdtemp(prefix="test_dockerfile")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.workdir)

    def setUp(self):
        # Prepare directory structure
        self.target = os.path.join(self.workdir, "target")
        os.makedirs(os.path.join(self.target, 'image'))
        self.dockerfile = os.path.join(self.target, "image", "Dockerfile")

        # create default descriptor
        self.descriptor = basic_config.copy()

        # prepare Generator + inject required deps
        self.generator = Generator.__new__(Generator)
        self.generator.target = self.target
        self.generator.effective_descriptor = Descriptor.__new__(Descriptor)
        self.generator.effective_descriptor.descriptor = self.descriptor
        

    def tearDown(self):
        shutil.rmtree(self.target)

    def test_set_cmd_user(self):
        """
        Ensure that setting a user in the YAML generates a corresponding
        USER instruction in the Dockerfile, immediately before the CMD.
        """
        self.descriptor['user'] = 1347
        self.generator.render_dockerfile()

        
        with open(self.dockerfile, "r") as f:
            dockerfile = f.read()
            regex = re.compile(r'.*USER 1347\n+CMD.*',
                               re.MULTILINE)
            self.assertRegexpMatches(dockerfile, regex)

    def test_set_cmd(self):
        """
        Test that cmd: is mapped into a CMD instruction
        """
        self.descriptor['cmd'] = ['/usr/bin/date']
        self.generator.render_dockerfile()

        with open(os.path.join(self.dockerfile), "r") as f:
            dockerfile = f.read()
            regex = re.compile(r'.*CMD \["/usr/bin/date"\]',
                               re.MULTILINE)
            self.assertRegexpMatches(dockerfile, regex)

    def test_set_entrypoint(self):
        """
        Test that entrypoint: is mapped into a ENTRYPOINT instruction
        """
        self.descriptor['entrypoint'] = ['/usr/bin/time']
        self.generator.render_dockerfile()

        with open(self.dockerfile, "r") as f:
            dockerfile = f.read()
            regex = re.compile(r'.*ENTRYPOINT \["/usr/bin/time"\]',
                               re.MULTILINE)
            self.assertRegexpMatches(dockerfile, regex)

    def test_volumes(self):
        """
        Test that cmd: is mapped into a CMD instruction
        """
        self.descriptor['volumes'] = ['/var/lib', '/usr/lib']
        self.generator.render_dockerfile()

        with open(self.dockerfile, "r") as f:
            dockerfile = f.read()
            regex = re.compile(r'.*VOLUME \["/var/lib"\]\nVOLUME \["/usr/lib"\]',  re.MULTILINE)
            self.assertRegexpMatches(dockerfile, regex)

    # https://github.com/jboss-dockerfiles/dogen/issues/124
    def test_debug_port(self):
        self.descriptor['ports'] = [{'value': 8080},
                                   {'expose': False,
                                    'value': 9999}]
        
        self.generator.render_dockerfile()

        with open(self.dockerfile, "r") as f:
            dockerfile = f.read()
            regex = re.compile(r'.*EXPOSE 8080$',  re.MULTILINE)
            self.assertRegexpMatches(dockerfile, regex)

    # https://github.com/jboss-dockerfiles/dogen/issues/127
    def test_generating_env_variables(self):
        self.descriptor['envs'] = [{'name': 'CONFIG_ENV',
                                    'example': 1234},
                                   {'name': 'COMBINED_ENV',
                                    'value': 'set_value',
                                    'example': 'example_value',
                                    'description': 'This is a description'}]

        self.generator.render_dockerfile()

        with open(self.dockerfile, "r") as f:
            dockerfile = f.read()
            regex = re.compile(r'ENV JBOSS_IMAGE_NAME=\"testimage\" \\\s+JBOSS_IMAGE_VERSION=\"1\" \\\s+COMBINED_ENV=\"set_value\" \n',  re.MULTILINE)
            self.assertRegexpMatches(dockerfile, regex)
