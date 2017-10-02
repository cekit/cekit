import tempfile
import unittest

from concreate.template_helper import TemplateHelper


class TestConfig(unittest.TestCase):

    def setUp(self):
        self.helper = TemplateHelper()

    def test_generate_component(self):
        self.assertEqual(self.helper.component(
            "jboss-eap-7/eap70"), "jboss-eap-7-eap70-docker")

    def test_generate_component_for_beta_image(self):
        self.assertEqual(self.helper.component(
            "jboss-eap-7-beta/eap70"), "jboss-eap-7-beta-eap70-docker")

    def test_generate_component_for_tech_preview_image(self):
        self.assertEqual(self.helper.component(
            "jboss-eap-7-tech-preview/eap70"), "jboss-eap-7-eap70-docker")
