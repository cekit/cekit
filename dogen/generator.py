# -*- coding: utf-8 -*-

import hashlib
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

SUPPORTED_HASH_ALGORITHMS = ['sha256', 'sha1', 'md5']

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

        self.log.debug("Fetched file will be saved as '%s'..." % os.path.basename(output))

        r = requests.get(location, verify=self.ssl_verify, stream=True)

        if r.status_code != 200:
            raise Error("Could not download file from %s" % location)

        with open(output, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                f.write(chunk)

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

        if 'user' not in self.cfg:
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

        if schema is None:
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

        self.handle_sources()
        self.render_from_template()

        for plugin in self.plugins:
            plugin.after_sources(files=self.cfg.get('artifacts'))

        self.log.info("Finished!")

    def render_from_template(self):
        if not self.cfg.get('labels'):
            self.cfg['labels'] = []

        # https://github.com/jboss-dockerfiles/dogen/issues/129
        # https://github.com/jboss-dockerfiles/dogen/issues/137
        for label in ['maintainer', 'description']:
            value = self.cfg.get(label)

            if value:
                self.cfg['labels'].append({'name': label, 'value': value})

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
        if 'sources' not in self.cfg or self.without_sources:
            return []

        self.log.info("Handling artifacts...")
        self.cfg['artifacts'] = {}

        sources_cache = os.environ.get("DOGEN_SOURCES_CACHE")
        self.log.debug("Source cache will be used for all artifacts")

        for source in self.cfg['sources']:
            url = source.get('url')
            artifact = source.get('artifact')

            if url:
                self.log.warn("The 'url' key is deprecated, please use 'artifact' for specifying the %s artifact location" % url)

                if artifact:
                    self.log.warn("You specified both: 'artifact' and 'url' for a source file, 'artifact': will be used: %s" % artifact)
                else:
                    # Backward compatibility
                    artifact = url

            if not artifact:
                raise Error("Artifact location for one or more sources was not provided, please check your image descriptor!")

            self.log.info("Handling artifact '%s'" % artifact)

            basename = os.path.basename(artifact)
            target = source.get('target')

            # In case we specify target name for the artifact - use it
            if not target:
                target = basename

            filename = ("%s/%s" % (self.output, target))

            passed = False
            algorithms = []

            md5sum = source.get('md5sum')

            if md5sum:
                self.log.warn("The 'md5sum' key is deprecated, please use 'md5' for %s. Or better switch to sha256 or sha1." % artifact)

                # Backwards compatibility for md5sum
                if not source.get('md5'):
                    source['md5'] = md5sum

            for supported_algorithm in SUPPORTED_HASH_ALGORITHMS:
                if not source.get(supported_algorithm):
                    continue

                algorithms.append(supported_algorithm)

            try:
                if os.path.exists(filename):
                    if algorithms:
                        for algorithm in algorithms:
                            self.check_sum(filename, source[algorithm], algorithm)
                    passed = True
            except Exception as e:
                self.log.debug(str(e))
                self.log.warn("Local file doesn't match provided checksum, artifact '%s' will be downloaded again" % artifact)
                passed = False

            if not passed:

                if sources_cache:
                    cached_artifact = sources_cache.replace('#filename#', basename)

                    if algorithms:
                        if len(algorithms) > 1:
                            self.log.warn("You specified multiple algorithms for '%s' artifact, but only '%s' will be used to fetch it from cache" % (artifact, algorithms[0]))

                        cached_artifact = cached_artifact.replace('#hash#', source[algorithms[0]]).replace('#algorithm#', algorithms[0])

                    try:
                        self._fetch_file(cached_artifact, filename)
                    except Exception as e:
                        self.log.warn("Could not download artifact from cached location: '%s': %s. Please make sure you set the correct value for DOGEN_SOURCES_CACHE (currently: '%s')." % (cached_artifact, str(e), sources_cache))
                        self._download_source(artifact, filename, source.get('hint'))
                else:
                    self._download_source(artifact, filename, source.get('hint'))

                if algorithms:
                    for algorithm in algorithms:
                        self.check_sum(filename, source[algorithm], algorithm)

            if algorithms:
                self.cfg['artifacts'][target] = "%s:%s" % (algorithms[0], source[algorithms[0]])
            else:
                self.log.warn("No checksum was specified for artifact '%s'!" % artifact)
                self.cfg['artifacts'][target] = None

    def _download_source(self, artifact, filename, hint=None):
        if Tools.is_url(artifact):
            self.log.warn("Trying to download the '%s' artifact from original location" % artifact)
            try:
                self._fetch_file(artifact, filename)
            except Exception as e:
                raise Error("Could not download artifact from orignal location, reason: %s" % str(e))
        else:
            if hint:
                self.log.info(hint)
            self.log.info("Please download the '%s' artifact manually and save it as '%s'" % (artifact, filename))
            raise Error("Artifact '%s' could not be fetched!" % artifact)

    def check_sum(self, filename, checksum, algorithm):
        self.log.debug("Checking '%s' %s hash..." % (os.path.basename(filename), algorithm))

        hash = getattr(hashlib, algorithm)()

        with open(filename, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hash.update(chunk)
        filesum = hash.hexdigest()

        if filesum.lower() != checksum.lower():
            raise Error("The %s computed for the '%s' file ('%s') doesn't match the '%s' value" % (algorithm, filename, filesum, checksum))

        self.log.debug("Hash is correct.")
