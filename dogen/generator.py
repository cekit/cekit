# -*- coding: utf-8 -*-

import hashlib
import glob
import os
import shutil
import requests
import yaml
import tempfile

from jinja2 import FileSystemLoader, Environment
from pykwalify.core import Core
from pykwalify.errors import SchemaError

from dogen.template_helper import TemplateHelper
from dogen.tools import Tools
from dogen import version, DEFAULT_SCRIPT_EXEC, DEFAULT_SCRIPT_USER
from dogen.errors import Error

class Generator(object):
    def __init__(self, log, args, plugins=[]):
        self.log = log
        self.pwd = os.path.realpath(os.path.dirname(os.path.realpath(__file__)))
        self.descriptor = os.path.realpath(args.path)
        self.without_sources = args.without_sources
        self.output = args.output
        self.dockerfile = os.path.join(self.output, "Dockerfile")
        self.template = args.template
        self.scripts_path = args.scripts_path
        self.additional_scripts = args.additional_script

        ssl_verify = None
        if args.skip_ssl_verification:
            ssl_verify = False
        self.ssl_verify = ssl_verify

        self.plugins = []
        for plugin in plugins:
            self.plugins.append(plugin(self, args))

    def _fetch_file(self, location, output=None):
        """
        Fetches remote file and saves it under output. If no
        output path is provided, a temporary file is created
        and path to this file is returned.

        SSL verification could be disabled by setting
        self.ssl_verify to False.
        """

        self.log.debug("Fetching '%s' file..." % location)

        if not output:
            output = tempfile.mktemp("-dogen")

        self.log.debug("Fetched file will be saved as '%s'..." % output)

        with open(output, 'wb') as f:
            f.write(requests.get(location, verify=self.ssl_verify).content)

        return output

    def _handle_custom_template(self):
        """
        Fetches custom template (if provided) and saves as temporary
        file. This file is removed later in the process.
        """

        if not self.template:
            return

        self.log.info("Using custom provided template file: '%s'" % self.template)

        if Tools.is_url(self.template):
            self.template = self._fetch_file(self.template)

        if not os.path.exists(self.template):
            raise Error("Template file '%s' could not be found. Please make sure you specified correct path or check if the file was successfully fetched." % self.template)


    def configure(self):
        """
        Reads configuration values from the descriptor, if provided.

        Some Dogen configuration values can be set in the YAML
        descriptor file using the 'dogen' section.
        """
        self._validate_cfg()

        if not self.scripts_path:
            # If scripts directory is not provided, see if there is a "scripts"
            # directory next to the descriptor. If found - assume that's the
            # directory containing scripts.
            scripts = os.path.join(os.path.dirname(self.descriptor), "scripts")
            if os.path.exists(scripts) and os.path.isdir(scripts):
                self.scripts_path = scripts

        if not 'user' in self.cfg:
            self.cfg['user'] = 0

        dogen_cfg = self.cfg.get('dogen')

        if not dogen_cfg:
            return

        required_version = dogen_cfg.get('version')

        if required_version:
            # Check if the current runnig version of Dogen
            # is the one the descriptor is expecting.
            if required_version != version:
                raise Error("You try to parse descriptor that requires Dogen version %s, but you run version %s" % (required_version, version))

        ssl_verify = dogen_cfg.get('ssl_verify')

        if self.ssl_verify is None and ssl_verify is not None:
            self.ssl_verify = ssl_verify

        template = dogen_cfg.get('template')

        if template and not self.template:
            self.template = template

        scripts = dogen_cfg.get('scripts_path')

        if scripts and not self.scripts_path:
            self.scripts_path = scripts

        additional_scripts = dogen_cfg.get('additional_scripts')

        if additional_scripts and not self.additional_scripts:
            self.additional_scripts = additional_scripts

        if self.scripts_path and not os.path.exists(self.scripts_path):
            raise Error("Provided scripts directory '%s' does not exist" % self.scripts_path)

    def _handle_scripts(self):
        if not self.cfg.get('scripts'):
            return

        for script in self.cfg['scripts']:
            package = script['package']
            src_path = os.path.join(self.scripts_path, package)
            output_path = os.path.join(self.output, "scripts", package)

            possible_exec = os.getenv('DOGEN_SCRIPT_EXEC', DEFAULT_SCRIPT_EXEC)

            if "exec" not in script and os.path.exists(os.path.join(src_path, possible_exec)):
                script['exec'] = possible_exec

            if "user" not in script:
                script['user'] = os.getenv('DOGEN_SCRIPT_USER', DEFAULT_SCRIPT_USER)

            # Poor-man's workaround for not copying multiple times the same thing
            if not os.path.exists(output_path):
                self.log.info("Copying package '%s'..." % package)
                shutil.copytree(src=src_path, dst=output_path)
                self.log.debug("Done.")

    def _handle_additional_scripts(self):
        self.log.info("Additional scripts provided, installing them...")
        output_scripts = os.path.join(self.output, "scripts")

        if not os.path.exists(output_scripts):
            os.makedirs(output_scripts)

        for f in self.additional_scripts:
            self.log.debug("Handling '%s' file..." % f)
            if Tools.is_url(f):
                self._fetch_file(f, os.path.join(output_scripts, os.path.basename(f)))
            else:
                if not (os.path.exists(f) and os.path.isfile(f)):
                    raise Error("File '%s' does not exist. Please make sure you specified correct path to a file when specifying additional scripts." % f)

                self.log.debug("Copying '%s' file to target scripts directory..." % f)
                shutil.copy(f, output_scripts)

    def _handle_custom_repo_files(self):
        self.cfg['additional_repos'] = []
        repo_files = glob.glob(os.path.join(self.output, "scripts", "*.repo"))

        if not repo_files:
            return

        self.log.debug("Found following additional repo files: %s" % ", ".join(repo_files))

        for f in repo_files:
            self.cfg['additional_repos'].append(os.path.splitext(os.path.basename(f))[0])

    def _validate_cfg(self):
        """
        Open and parse the YAML configuration file and ensure it matches
        our Schema for a Dogen configuration.
        """
        # Fail early if descriptor file is not found
        if not os.path.exists(self.descriptor):
            raise Error("Descriptor file '%s' could not be found. Please make sure you specified correct path." % self.descriptor)

        schema_path = os.path.join(self.pwd, "schema", "kwalify_schema.yaml")
        schema = {}
        with open(schema_path, 'r') as fh:
            schema = yaml.safe_load(fh)

        if schema == None:
            raise Error("couldn't read a valid schema at %s" % schema_path)

        for plugin in self.plugins:
            plugin.extend_schema(schema)

        with open(self.descriptor, 'r') as stream:
            self.cfg = yaml.safe_load(stream)

        c = Core(source_data=self.cfg, schema_data=schema)
        try:
            c.validate(raise_exception=True)
        except SchemaError as e:
            raise Error(e)

    def run(self):

        # Set Dogen settings if  provided in descriptor
        self.configure()

        # Special case for ssl_verify setting. Setting it to None
        # in CLI if --skip-ssl-verification is not set to make it
        # possible to determine which setting should be used.
        # This means that we need to se the ssl_verify to the
        # default value of True is not set.
        if self.ssl_verify is None:
            self.ssl_verify = True

        for plugin in self.plugins:
            plugin.prepare(cfg=self.cfg)

        if self.template:
            self._handle_custom_template()

        # Remove the target scripts directory
        shutil.rmtree(os.path.join(self.output, "scripts"), ignore_errors=True)

        if not os.path.exists(self.output):
            os.makedirs(self.output)

        if self.scripts_path:
            self._handle_scripts()
        else:
            self.log.warn("No scripts will be copied, mistake?")

        # Additional scripts (not package scripts)
        if self.additional_scripts:
            self._handle_additional_scripts()

        self._handle_custom_repo_files()

        self.render_from_template()
        sources = self.handle_sources()

        for plugin in self.plugins:
            plugin.after_sources(files=sources)

        self.log.info("Finished!")

    def render_from_template(self):
        if self.template:
            template_file = self.template
        else:
            self.log.debug("Using dogen provided template file")
            template_file = os.path.join(self.pwd, "templates", "template.jinja")

        self.log.info("Rendering Dockerfile...")
        loader = FileSystemLoader(os.path.dirname(template_file))
        env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
        env.globals['helper'] = TemplateHelper()
        template = env.get_template(os.path.basename(template_file))

        with open(self.dockerfile, 'wb') as f:
            f.write(template.render(self.cfg).encode('utf-8'))
        self.log.debug("Done")

        if self.template and Tools.is_url(self.template):
            self.log.debug("Removing temporary template file...")
            os.remove(self.template)

    def handle_sources(self):
        if not 'sources' in self.cfg or self.without_sources:
            return []

        files = []

        for source in self.cfg['sources']:
            url = source['url']
            basename = os.path.basename(url)
            files.append(basename)
            filename = ("%s/%s" %(self.output, basename))
            passed = False
            try:
                if os.path.exists(filename):
                    self.check_sum(filename, source['md5sum'])
                    passed = True
            except:
                passed = False

            if not passed:
                sources_cache = os.environ.get("DOGEN_SOURCES_CACHE")
                if sources_cache:
                    self.log.info("Using '%s' as cached location for sources" % sources_cache)
                    url = "%s/%s" % (sources_cache, basename)

                self.log.info("Downloading '%s'..." % url)
                with open(filename, 'wb') as f:
                    f.write(requests.get(url, verify=self.ssl_verify).content)
                self.check_sum(filename, source['md5sum'])

        return files

    def check_sum(self, filename, checksum):
        self.log.info("Checking '%s' MD5 hash..." % os.path.basename(filename))
        filesum = hashlib.md5(open(filename, 'rb').read()).hexdigest()
        if filesum != checksum:
            raise Exception("The md5sum computed for the '%s' file ('%s') doesn't match the '%s' value" % (filename, filesum, checksum))
        self.log.debug("MD5 hash is correct.")
