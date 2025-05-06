# -*- encoding: utf-8 -*-

from __future__ import print_function

import logging
import os
import shutil
import sys

from _pytest.capture import CaptureResult
from click.testing import CliRunner

from cekit.cli import cli
from cekit.tools import Chdir
from cekit.version import __version__


def run_cekit(image_dir, args=None, env=None):
    if args is None:
        args = ["-v", "build", "podman"]

    if env is None:
        env = {}

    with Chdir(image_dir):
        print(f"Using image_dir={image_dir}")
        result = CliRunner(env=env).invoke(cli, args, catch_exceptions=False)
        sys.stdout.write("\n")
        sys.stdout.write(result.output)
        assert result.exit_code == 0
        return result


def test_podman_builder_with_alpine_image(tmpdir, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")
    tmpdir = str(tmpdir)

    shutil.copytree(
        os.path.join(os.path.dirname(__file__), "images", "alpine"),
        os.path.join(tmpdir, "alpine"),
    )

    # The 'BUILDAH_LAYERS' environment variable is required to not cache intermediate layers
    # See: https://bugzilla.redhat.com/show_bug.cgi?id=1746022
    run_cekit(os.path.join(tmpdir, "alpine"), env={"BUILDAH_LAYERS": "false"})

    print(f"#### Caplog {caplog.text} ####")
    assert (
        """STEP 11/12: RUN :     && rm -rf "/var/cache/yum" "/var/lib/dnf" "/var/cache/apt" "/var/cache/dnf"
"""
        in caplog.text
    )


def test_podman_builder_with_alpine_image_and_no_squash(tmpdir, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")
    tmpdir = str(tmpdir)

    shutil.copytree(
        os.path.join(os.path.dirname(__file__), "images", "alpine"),
        os.path.join(tmpdir, "alpine"),
    )

    # The 'BUILDAH_LAYERS' environment variable is required to not cache intermediate layers
    # See: https://bugzilla.redhat.com/show_bug.cgi?id=1746022
    run_cekit(
        os.path.join(tmpdir, "alpine"),
        env={"BUILDAH_LAYERS": "false"},
        args=["-v", "build", "podman", "--no-squash"],
    )
    assert (
        """STEP 5/11: RUN :         && apk  add python3             && apk info -e python3         && :         && rm -rf "/var/cache/yum" "/var/lib/dnf" "/var/cache/apt" "/var/cache/dnf"         && :"""
        in caplog.text
    )

    with open(
        os.path.join(str(tmpdir), "alpine/target/image/Containerfile"), "r"
    ) as _file:
        containerFile = _file.read()
        assert (
            """###### START module 'app:1.0'
###### \\
        # Copy 'app' module content
        COPY modules/app /tmp/scripts/app
        # Switch to 'root' user for package management for 'app' module defined packages
        USER root
        RUN : \\
        # Install packages defined in the 'app' module
        && apk  add python3 \\
            && apk info -e python3 \\
        # Clear package manager metadata
        && : \\
        && rm -rf "/var/cache/yum" "/var/lib/dnf" "/var/cache/apt" "/var/cache/dnf" \\
        && :

        # Custom scripts from 'app' module
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/app/install.sh" ]
###### /
###### END module 'app:1.0'

###### START image 'cekit-alpine:1.0.0'
###### \\
        # Set 'cekit-alpine' image defined labels
        LABEL \\
            description="Some Alpine image" \\
            io.cekit.version="VVVVV" \\
            summary="Some Alpine image"
###### /
###### END image 'cekit-alpine:1.0.0'



    # Switch to 'root' user and remove artifacts and modules
    USER root
    RUN rm -rf "/tmp/scripts" "/tmp/artifacts"
    # Define the user
    USER root""".replace(
                "VVVVV", __version__
            )
            in containerFile
        )


def test_podman_from_scratch(tmpdir):
    tmpdir = str(tmpdir)

    shutil.copytree(
        os.path.join(os.path.dirname(__file__), "images", "scratch"),
        os.path.join(tmpdir, "scratch"),
    )

    # The 'BUILDAH_LAYERS' environment variable is required to not cache intermediate layers
    # See: https://bugzilla.redhat.com/show_bug.cgi?id=1746022
    run_cekit(os.path.join(tmpdir, "scratch"), env={"BUILDAH_LAYERS": "false"})


def test_podman_operator_metadata(tmpdir, capfd):
    tmpdir = str(tmpdir)

    shutil.copytree(
        os.path.join(os.path.dirname(__file__), "images", "operator-metadata"),
        os.path.join(tmpdir, "operator-metadata"),
    )

    # The 'BUILDAH_LAYERS' environment variable is required to not cache intermediate layers
    # See: https://bugzilla.redhat.com/show_bug.cgi?id=1746022
    run_cekit(
        os.path.join(tmpdir, "operator-metadata"),
        args=["--redhat", "--trace", "build", "podman"],
        env={"BUILDAH_LAYERS": "false"},
    )

    output: CaptureResult = capfd.readouterr()
    print(output.err)
    assert 'level=debug msg="Called build.PersistentPreRunE' in output.err
    assert (
        "Successfully tagged localhost/amq7/amq-streams-rhel7-operator-metadata:latest"
        in output.out
    )
