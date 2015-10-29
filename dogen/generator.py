# -*- coding: utf-8 -*-

import argparse
import hashlib
import getpass
import os
import shutil
import sys
import urllib
import yaml
import subprocess

from jinja2 import FileSystemLoader, Environment

from dogen.git import Git
from dogen.template_helper import TemplateHelper

class Generator(object):
    def __init__(self, log, template, output, scripts=None, without_sources=False, dist_git=False):
        self.log = log
        self.uid = os.stat(template).st_uid
        self.gid = os.stat(template).st_gid

        with open(template, 'r') as stream:
            self.cfg = yaml.safe_load(stream)

        self.input = os.path.realpath(os.path.dirname(os.path.realpath(template)))
        self.output = output
        self.scripts = scripts

        self.template = template
        self.pwd = os.path.realpath(os.path.dirname(os.path.realpath(__file__)))
        self.without_sources = without_sources
        self.dist_git = dist_git

        self.dockerfile = os.path.join(self.output, "Dockerfile")

        if self.dist_git:
            self.git = Git(self.log, os.path.dirname(self.input), self.output)

    def run(self):
        if self.dist_git:
            self.git.prepare()


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

        self.render_from_template()
        self.handle_sources()
        self.change_owners()

        if self.dist_git:
            self.git.update()

    def change_owners(self):
        """
        Changes the owner of the generated files to the same user
        as the owner of the mounted template
        """
        self.log.debug("Changing owner of generated files to: %s:%s..." % (self.uid, self.gid))
        os.chown(self.output, self.uid, self.gid)
        for root, dirs, files in os.walk(self.output):
            for d in dirs:
                os.chown(os.path.join(root, d), self.uid, self.gid)
            for f in files:
                os.chown(os.path.join(root, f), self.uid, self.gid)
        self.log.debug("Done.")

    def render_from_template(self):
        self.log.info("Rendering Dockerfile...")
        loader = FileSystemLoader(os.path.join(self.pwd, "templates"))
        env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
        env.globals['helper'] = TemplateHelper()
        template = env.get_template("template.jinja")

        with open(self.dockerfile, 'w') as f:
            f.write(template.render(self.cfg).encode('utf-8'))
        self.log.debug("Done.")

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
                urllib.urlretrieve(url, filename)
                self.check_sum(filename, source['hash'])

        if self.dist_git:
            self.git.update_lookaside_cache(files)

    def check_sum(self, filename, checksum):
        self.log.info("Checking '%s' hash..." % os.path.basename(filename))
        filesum = hashlib.md5(open(filename, 'rb').read()).hexdigest()
        if filesum != checksum:
            raise Exception("The md5sum computed for the '%s' file ('%s') doesn't match the '%s' value" % (filename, filesum, checksum))
        self.log.debug("Hash is correct.")



