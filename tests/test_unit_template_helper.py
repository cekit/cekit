from concreate.template_helper import TemplateHelper


helper = TemplateHelper()


def test_generate_component():
    assert helper.component("jboss-eap-7/eap70") == "jboss-eap-7-eap70-docker"


def test_generate_component_for_beta_image():
    assert helper.component("jboss-eap-7-beta/eap70") == "jboss-eap-7-beta-eap70-docker"


def test_generate_component_for_tech_preview_image():
    assert helper.component("jboss-eap-7-tech-preview/eap70") == "jboss-eap-7-eap70-docker"


def test_filter_state():
    candidates = [{'name': 'foo',
                   'state': 'present'},
                  {'name': 'bar',
                   'state': 'absent'},
                  {'name': 'baz',
                   'state': 'present'}]

    assert helper.filter_state(candidates, 'present') == ['foo', 'baz']
    assert helper.filter_state(candidates, 'absent') == ['bar']
