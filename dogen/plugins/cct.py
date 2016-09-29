import os
import yaml
import subprocess
import shutil

from dogen.plugin import Plugin


class CCT(Plugin):
    @staticmethod
    def info():
        return "cct", "Support for configuring images via cct"

    def __init__(self, dogen, args):
        super(CCT, self).__init__(dogen, args)

    def extend_schema(self, parent_schema):
        """
        Read in a schema definition for our part of the config and hook it
        into the parent schema at the cct: top-level key.
        """
        schema_path = os.path.join(self.dogen.pwd, "schema", "cct_schema.yaml")
        schema = {}
        with open(schema_path, 'r') as fh:
            schema = yaml.safe_load(fh)

        parent_schema['map']['cct'] = schema

    def prepare(self, cfg):
        """
        create cct changes yaml file for image.yaml template decscriptor
        it require cct aware template.jinja file
        """
        # check if cct plugin has any steps to perform (prevent it from raising ugly exceptions)
        if not 'cct' in cfg:
            self.log.debug("No cct key in image.yaml - nothing to do")
            return

        if os.path.exists(self.output + '/cct/'):
            shutil.rmtree(self.output + '/cct/')

        if 'modules' in cfg['cct']:
            self._prepare_modules(cfg)

        cfg['cct']['run'] = ['cct.yaml']

        cfg_file_dir = os.path.join(self.output, "cct")
        if not os.path.exists(cfg_file_dir):
            os.makedirs(cfg_file_dir)

        cfg_file = os.path.join(cfg_file_dir, "cct.yaml")
        with open(cfg_file, 'w') as f:
            yaml.dump(cfg['cct']['configure'], f)

        if 'runtime' in cfg['cct']:
            self.runtime_changes(cfg)

        if not 'user' in cfg['cct']:
            cfg['cct']['user'] = 'root'

    def _prepare_modules(self, cfg):
        for module in cfg['cct']['modules']:
            name = None
            if 'name' in module:
                name = module['name']
            elif module['path'][-1] == '/':
                name = os.path.basename(module['path'][0:-1])
            elif len(module['path']) > 4 and module['path'][-4:] == ".git":
                name = os.path.basename(module['path'][0:-4])
            else:
                name = os.path.basename(module['path'])
            descriptor_dir = os.path.dirname(self.descriptor) + '/cct/'
            # check if module exists in cct dir next to do descriptor
            if os.path.exists(descriptor_dir + name):
                # path exists - I'll just copy it
                shutil.copytree(descriptor_dir + name,
                                self.output + '/cct/' + name)
                self.log.info("Copied cct module %s." % name)
            else:
                # clone it to target dir if not exists
                self.clone_repo(module['path'], self.output + '/cct/' + name)
                self.log.info("Cloned cct module %s." % name)
            try:
                self.append_sources(name, cfg)
            except Exception as ex:
                self.log.info("cannot process sources for module %s" % name)
                self.log.debug("exception: %s" % ex)

    def clone_repo(self, url, path):
        try:
            if not os.path.exists(path):
                subprocess.check_call(["git", "clone", url, path])
        except Exception as ex:
            self.log.error("cannot clone repo %s into %s: %s", url, path, ex)

    def append_sources(self, module, cfg):
        """
        Extract sources defined within the module, if provided, and merge
        them with Dogen's master sources list.
        """
        sources_path = os.path.join(self.output, "cct", module, "sources.yaml")

        if not os.path.exists(sources_path):
            self.log.debug("no sources defined for module %s" % module)
            return

        source_prefix = os.getenv("DOGEN_CCT_SOURCES_PREFIX") or ""
        if not source_prefix:
            self.log.debug("DOGEN_CCT_SOURCES_PREFIX variable is not defined")

        cct_sources = []
        with open(sources_path) as f:
            cct_sources = yaml.load(f)

        dogen_sources = []
        for source in cct_sources:
            dogen_source = {}
            dogen_source['url'] = source_prefix + source['name']
            dogen_source['md5sum'] = source['md5sum']
            dogen_sources.append(dogen_source)
        try:
            cfg['sources'].extend(dogen_sources)
        except:
            cfg['sources'] = dogen_sources

    def runtime_changes(self, cfg):
        """
        Handle configuring CCT for runtime use.

        User may supply a /cct/runtime key which will be written out as
        instructions for cct to execute at runtime.
        """

        # write out a cctruntime.yaml file from the /cct/runtime_changes key
        cfg_file_dir = os.path.join(self.output, "cct")
        if not os.path.exists(cfg_file_dir):
            os.makedirs(cfg_file_dir)
        cfg_file = os.path.join(cfg_file_dir, "cctruntime.yaml")
        with open(cfg_file, 'w') as f:
            yaml.dump(cfg['cct']['runtime'], f)

        # adjust cfg object so template adds the above to ENTRYPOINT
        if not 'runtime_changes' in cfg['cct']:
            cfg['cct']['runtime_changes'] = "/tmp/cct/cctruntime.yaml"

