import logging
import sys

import click

from cekit.cache.artifact import ArtifactCache
from cekit.config import Config
from cekit.crypto import SUPPORTED_HASH_ALGORITHMS
from cekit.descriptor import Resource
from cekit.log import setup_logging
from cekit.tools import Map
from cekit.version import version

setup_logging()
logger = logging.getLogger('cekit')
config = Config()


@click.group(context_settings=dict(max_content_width=100))
@click.option('-v', '--verbose', help="Enable verbose output.", is_flag=True)
@click.option('--config', metavar="PATH", help="Path to configuration file.", default="~/.cekit/config", show_default=True)
@click.option('--work-dir', metavar="PATH", help="Location of the working directory.", default="~/.cekit", show_default=True)
@click.version_option(message="%(version)s", version=version)
def cli(config, verbose, work_dir):
    pass


@cli.command(name="ls", short_help="List cached artifacts")
def ls():
    CacheCli.prepare().ls()


@cli.command(name="add", short_help="Add artifact to cache")
@click.argument('location', metavar="LOCATION")
@click.option('--md5', metavar="CHECKSUM", help="The md5 checksum of the artifact.")
@click.option('--sha1', metavar="CHECKSUM", help="The sha1 checksum of the artifact.")
@click.option('--sha256', metavar="CHECKSUM", help="The sha256 checksum of the artifact.")
def add(location, md5, sha1, sha256):
    if not (md5 or sha1 or sha256):
        raise click.UsageError("At least one checksum must be provided")

    CacheCli.prepare().add(location, md5, sha1, sha256)


@cli.command(name="rm", short_help="Remove artifact from cache")
@click.argument('uuid', metavar="UUID")
def rm(uuid):
    CacheCli.prepare().rm(uuid)


class CacheCli():
    @staticmethod
    def prepare():
        """ Returns an initialized object of CacheCli """
        return CacheCli(Map(click.get_current_context().parent.params))

    def __init__(self, args):

        # TODO: logging is used only when adding the artifact, we need to find out if it would be possible to do it better
        if args.verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        config.configure(args.config, {'work_dir': args.work_dir})

    def add(self, location, md5, sha1, sha256):
        artifact_cache = ArtifactCache()

        resource = {}
        resource['url'] = location

        if md5:
            resource['md5'] = md5

        if sha1:
            resource['sha1'] = sha1

        if sha256:
            resource['sha256'] = sha256

        artifact = Resource(resource)

        cached = artifact_cache.cached(artifact)

        if cached:
            click.echo("Artifact {} is already cached!".format(location))
            sys.exit(0)

        try:
            artifact_id = artifact_cache.add(artifact)
            click.echo("Artifact {} cached with UUID '{}'".format(location, artifact_id))
        except Exception as ex:
            click.secho("Cannot cache artifact {}: {}".format(location, str(ex)), fg='red')
            sys.exit(1)

    def ls(self):
        artifact_cache = ArtifactCache()
        artifacts = artifact_cache.list()
        if artifacts:
            for artifact_filename, artifact in artifacts.items():
                click.echo("\n{}:".format(click.style(
                    artifact_filename.split('.')[0], fg='green', bold=True)))
                for alg in SUPPORTED_HASH_ALGORITHMS:
                    if alg in artifact and artifact[alg]:
                        click.echo("  {}: {}".format(click.style(alg, bold=True), artifact[alg]))

                if artifact['names']:
                    click.echo("  {}:".format(click.style("names", bold=True)))
                    for name in artifact['names']:
                        click.echo("    - %s" % name)
        else:
            click.echo('No artifacts cached!')

    def rm(self, uuid):
        artifact_cache = ArtifactCache()

        try:
            artifact_cache.delete(uuid)
            click.echo("Artifact with UUID '{}' removed".format(uuid))
        except Exception:
            click.secho("Artifact with UUID '{}' doesn't exists in the cache".format(uuid), fg='yellow')
            sys.exit(1)


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
