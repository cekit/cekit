# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from dogen.generator import Generator
from dogen.version import version
from dogen.errors import Error

class MyParser(argparse.ArgumentParser):

    def error(self, message):
        self.print_help()
        sys.stderr.write('\nError: %s\n' % message)
        sys.exit(2)


class CLI(object):

    def __init__(self):
        self.log = logging.getLogger()
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

    def run(self):
        parser = MyParser(
            description='Dockerfile generator tool')

        parser.add_argument(
            '-v', '--verbose', action='store_true', help='Verbose output')

        parser.add_argument(
            '--version', action='version', help='Show version and exit', version=version)

        parser.add_argument('--without-sources', '--ws', action='store_true', help='Do not process sources, only generate Dockerfile')
        parser.add_argument('--dist-git', action='store_true', help='Specifies if the target directory is a dist-git repository')
        parser.add_argument('--scripts', help='Location of the scripts directory')

        parser.add_argument('template', help="Path to yaml template to process")
        parser.add_argument('output', help="Path to directory where generated files should be saved")

        args = parser.parse_args()

        if args.verbose:
            self.log.setLevel(logging.DEBUG)
        else:
            self.log.setLevel(logging.INFO)

        self.log.debug("Running version %s", version)

        try:
            Generator(args.template, args.output, scripts=args.scripts, without_sources=args.without_sources, dist_git=args.dist_git).run()
        except KeyboardInterrupt as e:
            pass
        except Error as e:
            self.log.exception(e)
            sys.exit(1)


def run():
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    run()
