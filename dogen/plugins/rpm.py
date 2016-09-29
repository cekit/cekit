import os
import shutil
import glob

from dogen.plugin import Plugin

class RPM(Plugin):
    @staticmethod
    def info():
        return "rpm","Support for injecting custom rpms"

    def __init__(self, dogen, args):
        super(RPM, self).__init__(dogen, args)
        self.rpms_directory = os.path.join(os.path.dirname(self.descriptor), "rpms")

    def extend_schema(self, parent_schema):
        """
        Extend the Dogen configuration schema to have a top-level list of
        strings at the 'rpms:' key
        """
        parent_schema['map']['rpms'] = {'seq':[{'type':'str'}],}

    def prepare(self, cfg):
        if not os.path.exists(self.rpms_directory):
            return
        self.log.info("Injecting custom rpms from %s" %self.rpms_directory)
        rpms_path = os.path.join(self.output, "rpms")
        if os.path.exists(rpms_path):
            shutil.rmtree(rpms_path)
        shutil.copytree(src=self.rpms_directory, dst=rpms_path)

        rpms = glob.glob(os.path.join(self.output, "rpms", "*.rpm"))

        self.log.debug("Found following additional rpm files: %s" % ", ".join(rpms))
        cfg['rpms'] = []
        for f in rpms:
            cfg['rpms'].append(os.path.basename(f))
