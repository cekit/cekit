import os
import sys

import pytest
import yaml
from click.testing import CliRunner

from cekit.cli import cli
from cekit.tools import Chdir


def run_cekit(image_dir, descriptor, args=None):
    if args is None:
        args = ["build", "--dry-run", "docker"]

    with Chdir(image_dir):
        with open("image.yaml", "w") as fd:
            yaml.dump(descriptor, fd, default_flow_style=False)

        result = CliRunner().invoke(cli, args, catch_exceptions=False)
        sys.stdout.write("\n")
        sys.stdout.write(result.output)

        assert result.exit_code == 0
        return result


@pytest.mark.skipif(
    os.path.exists("/var/run/docker.sock") is False, reason="No Docker available"
)
def test_module_uses_installed_package_in_execute_script(tmp_path, caplog):
    """Check that when a module has an install script that depends on packages that should be installed in an image,
    the install script succeeds.
    """

    image_dir = tmp_path / "image"
    module_dir = image_dir / "modules"

    image_dir.mkdir(exist_ok=True)

    # Build the module
    module_dir.mkdir(exist_ok=True)

    install_script = module_dir / "install.sh"
    install_script.write_text("\n".join(["#!/bin/bash", "zip --version"]))

    module_descriptor_file = module_dir / "module.yaml"
    module_descriptor_file.write_text(
        yaml.dump(
            {
                "name": "test_module",
                "version": "1.0",
                "execute": [{"script": str(install_script.name)}],
                "packages": {"manager": "apk", "install": ["zip"]},
            }
        )
    )

    image_descriptor = {
        "name": "test_image",
        "version": "1.0",
        "from": "alpine:latest",
        "modules": {
            "repositories": [{"name": "modules", "path": "modules/"}],
            "install": [{"name": "test_module"}],
        },
    }

    run_cekit(image_dir, image_descriptor, args=["-v", "build", "docker"])

    assert "Applying module package manager of apk to image" in caplog.text


@pytest.mark.skipif(
    os.path.exists("/var/run/docker.sock") is False, reason="No Docker available"
)
def test_module_uses_installed_package_in_execute_script_manager_precedence(
    tmp_path, caplog
):
    """Check that when a module has an install script that depends on packages that should be installed in an image,
    the install script succeeds and that the image manager takes precedence over modules
    """

    image_dir = tmp_path / "image"
    module_dir = image_dir / "modules"

    image_dir.mkdir(exist_ok=True)

    # Build the module
    module_dir.mkdir(exist_ok=True)

    install_script = module_dir / "install.sh"
    install_script.write_text("\n".join(["#!/bin/bash", "zip --version"]))

    module_descriptor_file = module_dir / "module.yaml"
    module_descriptor_file.write_text(
        yaml.dump(
            {
                "name": "test_module",
                "version": "1.0",
                "execute": [{"script": str(install_script.name)}],
                "packages": {"manager": "dnf", "install": ["zip"]},
            }
        )
    )

    image_descriptor = {
        "name": "test_image",
        "version": "1.0",
        "from": "alpine:latest",
        "modules": {
            "repositories": [{"name": "modules", "path": "modules/"}],
            "install": [{"name": "test_module"}],
        },
        "packages": {"manager": "apk"},
    }

    run_cekit(image_dir, image_descriptor, args=["-v", "build", "docker"])

    assert "Applying module package manager of apk to image" not in caplog.text
