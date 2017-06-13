# -*- coding: utf-8 -*-

import argparse
import logging
import requests
import sys
import os
import glob
import imp
import inspect

from dogen.generator import Generator
from dogen.version import version
from dogen.errors import Error
from dogen.plugin import Plugin

import colorlog

# Source: http://stackoverflow.com/questions/1383254/logging-streamhandler-and-standard-streams
# Adjusted
class SingleLevelFilter(logging.Filter):
    def __init__(self, passlevel, reject):
        self.passlevel = passlevel
        self.reject = reject

    def filter(self, record):
        if self.reject:
            return (record.levelno > self.passlevel)
        else:
            return (record.levelno <= self.passlevel)

class MyParser(argparse.ArgumentParser):

    def error(self, message):
        self.print_help()
        sys.stderr.write('\nError: %s\n' % message)
        sys.exit(2)

class CLI(object):

    def __init__(self):
        handler_out = logging.StreamHandler(sys.stdout)
        handler_err = logging.StreamHandler(sys.stderr)

        handler_out.addFilter(SingleLevelFilter(logging.INFO, False))
        handler_err.addFilter(SingleLevelFilter(logging.INFO, True))

        formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

        handler_out.setFormatter(formatter)
        handler_err.setFormatter(formatter)

        self.log = logging.getLogger("dogen")
        self.log.addHandler(handler_out)
        self.log.addHandler(handler_err)

        for package in ["requests.packages.urllib3", "pykwalify.rule"]:
            log = logging.getLogger(package)
            log.setLevel(logging.INFO)

        requests.packages.urllib3.disable_warnings()

    def run(self):
        parser = MyParser(
            description='Dockerfile generator tool', formatter_class=argparse.RawDescriptionHelpFormatter)

        epilog = "List of available plugins:\n"

        plugins = self.get_plugins()

        parser.add_argument(
            '-v', '--verbose', action='store_true', help='Verbose output')

        parser.add_argument(
            '--version', action='version', help='Show version and exit', version=version)

        parser.add_argument('--without-sources', '--ws', action='store_true', help='Do not process sources, only generate Dockerfile')
        parser.add_argument('--skip-ssl-verification', action='store_true', help='Should we skip SSL verification when retrieving data?')
        parser.add_argument('--scripts-path', help='Location of the scripts directory containing script packages.')
        parser.add_argument('--template', help='Path to custom template (can be url)')

        parser.add_argument('path', help="Path to yaml descriptor to process")
        parser.add_argument('output', help="Path to directory where generated files should be saved")

        for plugin in plugins:
            key, description = plugins[plugin].info()
            epilog += "\n  * %s:\t%s" % (key, description)
            parser = plugins[plugin].inject_args(parser)

        parser.epilog = epilog
        args = parser.parse_args()

        if args.verbose:
            self.log.setLevel(logging.DEBUG)
        else:
            self.log.setLevel(logging.INFO)


        self.log.debug("Running version %s", version)

        enabled_plugins = []

        for plugin in plugins:
            enabled_plugins.append(plugins[plugin])

        try:
            Generator(self.log, args=args, plugins=enabled_plugins).run()
        except KeyboardInterrupt as e:
            pass
        except Error as e:
            if args.verbose:
                self.log.exception(e)
            else:
                self.log.error(str(e))
            sys.exit(1)

    def get_plugins(self):
        """
        Finds all modules in the subdirs of directory
        """
        modules = {}
        directory = os.path.join(os.path.dirname(__file__), "plugins")
        for candidate in glob.glob(directory + os.sep + "*py"):
            self.log.debug("inspecting %s" %candidate)
            module_name = "dogen.plugins"
            self.log.debug("importing module %s to %s" % (os.path.abspath(candidate), module_name))
            module = imp.load_source(module_name, os.path.abspath(candidate))
            # Get all classes from our module
            for name, clazz in inspect.getmembers(module, inspect.isclass):
                # Check that class is from our namespace
                if module_name == clazz.__module__:
                    # Instantiate class
                    cls = getattr(module, name)
                    if issubclass(cls, Plugin):
                        self.log.info("found %s" %cls)
                        modules[cls.__name__] = cls
        return modules

def run():
    cli = CLI()
    cli.run()

if __name__ == "__main__":
    run()
