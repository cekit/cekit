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

        rpms = glob.glob(os.path.join(self.rpms_directory, "*.rpm"))

        if not rpms:
            self.log.debug("No RPMs found to be installed, skipping RPM plugin")
            return

        target_rpms = glob.glob(os.path.join(self.output, "*.rpm"))

        self.log.debug("Cleaning up target directory from stalled RPMs, to remove: %s" % ", ".join(target_rpms))

        for rpm in target_rpms:
            os.remove(rpm)

        self.log.debug("Cleaned up.")

        self.log.info("Injecting RPMs from %s" % self.rpms_directory)

        for rpm in rpms:
            shutil.copy2(rpm, self.output)

        self.log.debug("Found following additional rpm files: %s" % ", ".join(rpms))

        cfg['rpms'] = []

        for f in rpms:
            cfg['rpms'].append(os.path.basename(f))
