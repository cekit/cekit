import argparse
import logging
import sys
import traceback

from cekit.config import Config
from cekit.log import setup_logging
from cekit.crypto import SUPPORTED_HASH_ALGORITHMS
from cekit.cache.artifact import ArtifactCache
from cekit.descriptor import Resource
from cekit.version import version

# FIXME we shoudl try to move this to json
setup_logging()
logger = logging.getLogger('cekit')
config = Config()


class MyParser(argparse.ArgumentParser):

    def error(self, message):
        self.print_help()
        sys.stderr.write('\nError: %s\n' % message)
        sys.exit(2)


class CacheCli():

    def parse(self):
        parser = MyParser(
            description='Cekit cache manager',
            formatter_class=argparse.RawDescriptionHelpFormatter)

        parser.add_argument('-v',
                            '--verbose',
                            action='store_true',
                            help='verbose output')

        parser.add_argument('--version',
                            action='version',
                            help='show version and exit', version=version)

        parser.add_argument('--config',
                            default='~/.cekit/config',
                            help='path for Cekit config file (~/.cekit/config is default)')

        parser.add_argument('--work-dir',
                            dest='work_dir',
                            help="Location of Cekit working directory.")

        subparsers = parser.add_subparsers(dest='cmd')

        add = subparsers.add_parser('add',
                                    help='cache artifact from url')

        add.add_argument('url',
                         help='url of the artifact')

        for alg in SUPPORTED_HASH_ALGORITHMS:
            add.add_argument('--%s' % alg,
                             help='expected checksum of an object')

        subparsers.add_parser('ls',
                              help='list all cached artifacts')

        rm = subparsers.add_parser('rm',
                                   help='remove artifact by id')

        rm.add_argument('uuid',
                        help='uuid of an artifact which will be removed')

        self.args = parser.parse_args()

        return self

    def run(self):

        if self.args.verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        config.configure(self.args.config, {'work_dir': self.args.work_dir})

        if self.args.cmd == 'add':
            artifact_cache = ArtifactCache()

            resource = {}
            resource['url'] = self.args.url

            for alg in SUPPORTED_HASH_ALGORITHMS:
                val = getattr(self.args, alg)
                if val:
                    resource[alg] = val
            artifact = Resource(resource)

            if artifact_cache.is_cached(artifact):
                print('Artifact is already cached!')
                sys.exit(0)

            try:
                artifact_id = artifact_cache.add(artifact)
                if self.args.verbose:
                    print(artifact_id)
            except Exception as ex:
                if self.args.verbose:
                    traceback.print_exc()
                else:
                    print(ex)
                sys.exit(1)

        if self.args.cmd == 'ls':
            self.list()

        if self.args.cmd == 'rm':
            try:
                artifact_cache = ArtifactCache()
                artifact_cache.delete(self.args.uuid)
                print("Artifact removed")
            except Exception:
                print("Artifact doesn't exists")
                sys.exit(1)

        sys.exit(0)

    def list(self):
        artifact_cache = ArtifactCache()
        artifacts = artifact_cache.list()
        if artifacts:
            print("Cached artifacts:")
            for artifact_id, artifact in artifacts.items():
                print("%s:" % artifact_id)
                for alg in SUPPORTED_HASH_ALGORITHMS:
                    print("  %s: %s" % (alg, artifact[alg]))
                if artifact['names']:
                    print("  names:")
                    for name in artifact['names']:
                        print("    %s" % name)
        else:
            print('No artifacts cached!')


def run():
    CacheCli().parse().run()


if __name__ == "__main__":
    run()
