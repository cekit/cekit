import click
import logging
import sys
import traceback

from cekit.tools import Map
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


@click.group(context_settings=dict(max_content_width=100))
@click.option('-v', '--verbose', help="Enable verbose output.", is_flag=True)
@click.option('--config', help="Path to configuration file. [default: ~/.cekit/config]", default="~/.cekit/config")
@click.option('--work-dir', help="Location of the working directory. [default: ~/.cekit]", default="~/.cekit")
@click.version_option(message="%(version)s", version=version)
def cli(verbose, config, work_dir):
    pass


@cli.command(name="ls", short_help="List cached artifacts")
def ls():
    CacheCli(Map(click.get_current_context().parent.params)).ls()


@cli.command(name="add", short_help="Add artifact to cache")
@click.option('--location', help="URL or path pointing to the artifact", required=True)
# TODO Add checksums
def add(location):
    CacheCli(Map(click.get_current_context().parent.params)).add(location)


@cli.command(name="rm", short_help="Remove artifact from cache")
@click.option('--uuid', help="UUID of the artifact", required=True)
def rm(uuid):
    CacheCli(Map(click.get_current_context().parent.params)).rm(uuid)


class CacheCli():
    def __init__(self, args):
        self.args = args
        print(self.args)

        config.configure(self.args.config, {'work_dir': self.args.work_dir})

        if self.args.verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

    def add(self, location):
        artifact_cache = ArtifactCache()

        resource = {}
        resource['url'] = location

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

    def ls(self):
        artifact_cache = ArtifactCache()
        artifacts = artifact_cache.list()
        if artifacts:
            print("Cached artifacts:")
            for artifact_filename, artifact in artifacts.items():
                print("\n%s:" % artifact_filename.split('.')[0])
                for alg in SUPPORTED_HASH_ALGORITHMS:
                    if alg in artifact:
                        print("  %s: %s" % (alg, artifact[alg]))
                if artifact['names']:
                    print("  names:")
                    for name in artifact['names']:
                        print("    %s" % name)
        else:
            print('No artifacts cached!')

    def rm(self, uuid):
        try:
            artifact_cache = ArtifactCache()
            artifact_cache.delete(uuid)
            print("Artifact removed")
        except Exception:
            print("Artifact doesn't exists")
            sys.exit(1)


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
