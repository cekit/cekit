# -*- coding: utf-8 -*-

import argparse
import hashlib
import getpass
import glob
import os
import shutil
import sys
import requests
import urlparse
import yaml
import subprocess
import tempfile

from jinja2 import FileSystemLoader, Environment

from dogen.git import Git
from dogen.template_helper import TemplateHelper
from dogen.errors import Error

class Generator(object):
    def __init__(self, log, descriptor, output, template=None, scripts=None, additional_script=None, without_sources=False, dist_git=False, ssl_verify=True):
        self.log = log
        self.ssl_verify = ssl_verify
        self.template = template
        self.custom_template = False
        self.additional_script = additional_script

        if not os.path.exists(descriptor):
            raise Error("Descriptor file '%s' could not be found. Please make sure you specified correct path." % descriptor)

        self.pwd = os.path.realpath(os.path.dirname(os.path.realpath(__file__)))

        with open(descriptor, 'r') as stream:
            self.cfg = yaml.safe_load(stream)

        self.output = output
        self.scripts = scripts

        self.without_sources = without_sources
        self.dist_git = dist_git

        self.dockerfile = os.path.join(self.output, "Dockerfile")

        if self.dist_git:
            self.git = Git(self.log, os.path.dirname(os.path.realpath(descriptor)), self.output)

    def is_url(self, location):
        """ Checks if provided path is a URL """

        return bool(urlparse.urlparse(location).netloc)

    def fetch_file(self, location, output=None):
        """
        Fetches remote file and saves it under output. If no
        output path is provided, a temporary file is created
        and path to this file is returned.

        SSL verification could be disabled by setting
        self.ssl_verify to True.
        """

        self.log.debug("Fetching '%s' file..." % location)

        if not output:
            output = tempfile.mktemp("-dogen")
        
        self.log.debug("File will be saved as '%s'..." % output)

        with open(output, 'wb') as f:
            f.write(requests.get(location, verify=self.ssl_verify).content)

        return output
    
    def handle_custom_template(self):
        self.log.info("Using custom provided template file: '%s'" % self.template)
        self.custom_template = True

        if self.is_url(self.template):
            self.template = self.fetch_file(self.template)

        if not os.path.exists(self.template):
            raise Error("Template file '%s' could not be found. Please make sure you specified correct path or check if the file was successfully fetched." % self.template)

    def run(self):
        if self.dist_git:
            self.git.prepare()

        if self.template:
            self.handle_custom_template()
        else:
            self.log.debug("Using dogen provided template file")
            self.template = os.path.join(self.pwd, "templates", "template.jinja")

        # Remove the scripts directory
        shutil.rmtree(os.path.join(self.output, "scripts"), ignore_errors=True)

        if self.dist_git:
            self.git.clean_scripts()

        if not os.path.exists(self.output):
            os.makedirs(self.output)

        try:
            for scripts in self.cfg['scripts']:
                package = scripts['package']
                output_path = os.path.join(self.output, "scripts", package)
                try:
                    # Poor-man's workaround for not copying multiple times the same thing
                    if not os.path.exists(output_path):
                        self.log.info("Copying package '%s'..." % package)
                        shutil.copytree(src=os.path.join(self.scripts, package), dst=output_path)
                        self.log.debug("Done.")
                except Exception, ex:
                    self.log.exception("Cannot copy package %s" % package, ex)
        except KeyError:
            pass

        # Additional scripts (not package scripts)
        if self.additional_script:
            self.log.info("Additional scripts provided, installing them...")
            output_scripts = os.path.join(self.output, "scripts")

            if not os.path.exists(output_scripts):
                os.makedirs(output_scripts)

            for f in self.additional_script:
                self.log.debug("Handling '%s' file..." % f)
                if self.is_url(f):
                    self.fetch_file(f, os.path.join(output_scripts, os.path.basename(f)))
                else:
                    if not (os.path.exists(f) and os.path.isfile(f)):
                        raise Error("File '%s' does not exist. Please make sure you specified correct path to a file when specifying additional scripts." % f)

                    self.log.debug("Copying '%s' file to target scripts directory..." % f)
                    shutil.copy(f, output_scripts)

        self.render_from_template()
        self.handle_sources()

        if self.dist_git:
            self.git.update()

    def render_from_template(self):
        self.log.info("Rendering Dockerfile...")
        loader = FileSystemLoader(os.path.dirname(self.template))
        env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
        env.globals['helper'] = TemplateHelper()
        template = env.get_template(os.path.basename(self.template))

        with open(self.dockerfile, 'w') as f:
            f.write(template.render(self.cfg).encode('utf-8'))
        self.log.debug("Done")

        if self.custom_template:
            self.log.debug("Removing temporary template file...")
            os.remove(self.template)

    def handle_sources(self):
        if not 'sources' in self.cfg or self.without_sources:
            return

        files = []

        for source in self.cfg['sources']:
            url = source['url']
            basename = os.path.basename(url)
            files.append(basename)
            filename = ("%s/%s" %(self.output, basename))
            passed = False
            try:
                if os.path.exists(filename):
                    self.check_sum(filename, source['hash'])
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
                self.check_sum(filename, source['hash'])

        if self.dist_git:
            self.git.update_lookaside_cache(files)

    def check_sum(self, filename, checksum):
        self.log.info("Checking '%s' hash..." % os.path.basename(filename))
        filesum = hashlib.md5(open(filename, 'rb').read()).hexdigest()
        if filesum != checksum:
            raise Exception("The md5sum computed for the '%s' file ('%s') doesn't match the '%s' value" % (filename, filesum, checksum))
        self.log.debug("Hash is correct.")



