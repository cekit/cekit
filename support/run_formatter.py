#!/usr/bin/env python3
"""run_formatter.py - A tool to run the various formatters with the project settings"""
import logging
import sys
from pathlib import Path
from subprocess import CalledProcessError, run

import click

from cekit.log import setup_logging
from cekit.tools import Chdir

logger = logging.getLogger()


@click.command(
    help="Apply formatters to the project, using the project settings",
)
@click.option(
    "--check", help="Don't write the files back, just return the status.", is_flag=True
)
def main(check: bool) -> None:
    """Main function

    :params check: Flag to return the status without overwriting any file.
    """
    setup_logging()
    options = []
    if check:
        options.append("--check")

    repo_root = str(Path(__file__).parent.parent)
    logger.debug(f"Repository root is {repo_root}")

    # Run the various formatters, stop on the first error
    for formatter in [
        ["isort"],
        # black should be run last
        # ["black"],
    ]:
        try:
            with Chdir(repo_root):
                run(formatter + options + ["."], check=True)
        except CalledProcessError as err:
            sys.exit(err.returncode)

    sys.exit(0)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
