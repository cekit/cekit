import os
from cekit.docgen import Docgen
from cekit.builders.osbs import Chdir

def runtest_docgen(tmpdir,relmodule):
    module = os.path.join(os.path.dirname(__file__), relmodule)
    with Chdir(str(tmpdir)):
        link = os.path.basename(module)
        os.symlink(module, link)
        docgen = Docgen(link)
        docgen.docgen()
        assert os.path.exists("README.adoc")

def test_docgen_os_eap_s2i(tmpdir):
    runtest_docgen(tmpdir, "docgen/os-eap-s2i/module.yaml")

def test_docgen_os_eap7_ping(tmpdir):
    runtest_docgen(tmpdir, "docgen/os-eap7-ping/module.yaml")

def test_docgen_os_eap_logging(tmpdir):
    runtest_docgen(tmpdir, "docgen/os-eap-logging/module.yaml")
