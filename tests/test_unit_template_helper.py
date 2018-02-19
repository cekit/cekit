from concreate.descriptor.label import Label
from concreate.template_helper import TemplateHelper


helper = TemplateHelper()


def test_generate_component():
    component = helper.component("jboss-eap-7/eap70", None)
    assert component == 'com.redhat.component="jboss-eap-7-eap70-docker"'


def test_generate_component_exists():
    labels = [Label({'name': 'com.redhat.component',
                     'value': 'foo'})]
    component = helper.component("jboss-eap-7/eap70", labels)
    assert component == ''


def test_generate_component_for_beta_image():
    component = helper.component("jboss-eap-7-beta/eap70", None)
    assert component == 'com.redhat.component="jboss-eap-7-beta-eap70-docker"'


def test_generate_component_for_tech_preview_image():
    component = helper.component("jboss-eap-7-tech-preview/eap70", None)
    assert component == 'com.redhat.component="jboss-eap-7-eap70-docker"'
