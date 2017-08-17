# -*- coding: utf-8 -*-

import argparse
import os
import logging
import sys

from functools import partial

from dogen import tools
from dogen.errors import DogenError
from dogen.generator import Generator
from dogen.module import discover_modules, copy_image_module_to_repository
from dogen.version import version

logger = logging.getLogger('dogen')


class MyParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_help()
        sys.stderr.write('\nError: %s\n' % message)
        sys.exit(2)


class Dogen(object):
    """ Main application """

    def parse_args(self):
        parser = MyParser(
            description='Dockerfile generator tool',
            formatter_class=argparse.RawDescriptionHelpFormatter)

        parser.add_argument('-v',
                            '--verbose',
                            action='store_true',
                            help='Verbose output')

        parser.add_argument('--version',
                            action='version',
                            help='Show version and exit', version=version)

        parser.add_argument('--skip-ssl-verification',
                            action='store_true',
                            help='Should we skip SSL verification when retrieving data?')

        parser.add_argument('--template',
                            default=os.path.join(os.path.dirname(__file__),
                                                 'templates',
                                                 'template.jinja'),
                            help='Path to custom template (can be url)')

        parser.add_argument('descriptor_path',
                            help="Path to yaml descriptor to process")

        parser.add_argument('target',
                            help="Path to directory where generated files should be saved")

        self.args = parser.parse_args()
        return self

    def run(self):

        tools.artifact_fetcher = partial(tools.fetch_artifact,
                                         directory=self.args.target,
                                         ssl_verify=not self.args.skip_ssl_verification)

        if self.args.verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        logger.debug("Running version %s", version)
        try:
            copy_image_module_to_repository(
                os.path.join(os.path.dirname(self.args.descriptor_path),
                             'modules'),
                os.path.join(self.args.target,
                             'repo',
                             'modules'))

            discover_modules(os.path.join(self.args.target, 'repo'))

            generator = Generator(self.args.descriptor_path,
                                  self.args.target)
            generator.prepare_modules()
            generator.render_dockerfile(self.args.template)
            generator.fetch_artifacts()
        except KeyboardInterrupt as e:
            pass
        except DogenError as e:
            if self.args.verbose:
                self.log.exception(e)
            else:
                self.log.error(str(e))
            sys.exit(1)


if __name__ == "__main__":
    Dogen().parse_args().run()
