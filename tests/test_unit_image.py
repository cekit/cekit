import logging
from collections import OrderedDict

import pytest
import yaml

from cekit.descriptor import Image, Module, Overrides
from cekit.errors import CekitError
from cekit.generator.base import ModuleRegistry
from cekit.tools import Map


def test_image_overrides_with_content_sets_none():
    image = Image(
        yaml.safe_load(
            """
    from: foo
    name: test/foo
    version: 1.9
    packages:
      install:
        - abc
        - def
      content_sets:
        arch:
          - namea
          - nameb
    """
        ),
        "foo",
    )

    assert image.packages.content_sets == {"arch": ["namea", "nameb"]}
    assert "content_sets_file" not in image.packages

    image.apply_image_overrides(
        [Overrides({"packages": {"content_sets": None}}, "a/path")]
    )

    assert "content_sets" not in image.packages
    assert "content_sets_file" not in image.packages


def test_image_overrides_with_content_sets_file_none(mocker):
    with mocker.mock_module.patch(
        "cekit.descriptor.packages.os.path.exists"
    ) as exists_mock:
        exists_mock.return_value = True
        with mocker.mock_module.patch(
            "cekit.descriptor.packages.open",
            mocker.mock_open(read_data='{"arch": ["a", "b"]}'),
        ):
            image = Image(
                yaml.safe_load(
                    """
                from: foo
                name: test/foo
                version: 1.9
                packages:
                    install:
                        - abc
                         def
                    content_sets_file: cs.yaml
                """
                ),
                "foo",
            )

    assert image.packages.content_sets == {"arch": ["a", "b"]}
    assert "content_sets_file" not in image.packages

    image.apply_image_overrides(
        [Overrides({"packages": {"content_sets_file": None}}, "a/path")]
    )

    assert "content_sets" not in image.packages
    assert "content_sets_file" not in image.packages


def test_image_overrides_with_content_sets():
    image = Image(
        yaml.safe_load(
            """
    from: foo
    name: test/foo
    version: 1.9
    packages:
      install:
        - abc
        - def
      content_sets:
        arch:
          - namea
          - nameb
    """
        ),
        "foo",
    )

    assert image.packages.content_sets == {"arch": ["namea", "nameb"]}
    assert "content_sets_file" not in image.packages

    image.apply_image_overrides(
        [Overrides({"packages": {"content_sets": {"arch": ["new-arch"]}}}, "a/path")]
    )

    assert image.packages.content_sets == {"arch": ["new-arch"]}
    assert "content_sets_file" not in image.packages


def test_image_overrides_with_content_sets_file(mocker):
    image = Image(
        yaml.safe_load(
            """
    from: foo
    name: test/foo
    version: 1.9
    packages:
      install:
        - abc
        - def
      content_sets:
        arch:
          - namea
          - nameb
    """
        ),
        "foo",
    )

    assert image.packages.content_sets == {"arch": ["namea", "nameb"]}
    assert "content_sets_file" not in image.packages

    with mocker.mock_module.patch(
        "cekit.descriptor.packages.os.path.exists"
    ) as exists_mock:
        exists_mock.return_value = True
        with mocker.mock_module.patch(
            "cekit.descriptor.packages.open",
            mocker.mock_open(read_data='{"arch": ["a", "b"]}'),
        ):
            image.apply_image_overrides(
                [Overrides({"packages": {"content_sets_file": "some-path"}}, "a/path")]
            )

    assert image.packages.content_sets == {"arch": ["a", "b"]}
    assert "content_sets_file" not in image.packages


def test_image_overrides_packages_repositories_add():
    image = Image(
        yaml.safe_load(
            """
        from: foo
        name: test/foo
        version: 1.9
        packages:
            repositories:
                - name: scl
                  rpm: centos-release-scl
        """
        ),
        "foo",
    )

    assert len(image.packages.repositories) == 1
    assert image.packages.repositories[0].rpm == "centos-release-scl"
    assert image.packages.repositories[0].name == "scl"

    image.apply_image_overrides(
        [
            Overrides(
                {
                    "packages": {
                        "repositories": [{"id": "rhel7-extras-rpm", "name": "extras"}]
                    }
                },
                "a/path",
            )
        ]
    )

    assert len(image.packages.repositories) == 2
    assert image.packages.repositories[0].rpm == "centos-release-scl"
    assert image.packages.repositories[0].name == "scl"
    assert image.packages.repositories[1].id == "rhel7-extras-rpm"
    assert image.packages.repositories[1].name == "extras"


def test_image_overrides_packages_repositories_replace():
    image = Image(
        yaml.safe_load(
            """
        from: foo
        name: test/foo
        version: 1.9
        packages:
            repositories:
                - name: scl
                  rpm: centos-release-scl
        """
        ),
        "foo",
    )

    assert len(image.packages.repositories) == 1
    assert image.packages.repositories[0].rpm == "centos-release-scl"
    assert image.packages.repositories[0].name == "scl"

    image.apply_image_overrides(
        [
            Overrides(
                {
                    "packages": {
                        "repositories": [{"id": "rhel7-extras-rpm", "name": "scl"}]
                    }
                },
                "a/path",
            )
        ]
    )

    assert len(image.packages.repositories) == 1
    assert image.packages.repositories[0].name == "scl"
    assert image.packages.repositories[0].id == "rhel7-extras-rpm"
    assert "rpm" not in image.packages.repositories[0]


def test_module_processing_simple_modules_order_to_install():
    image = Image(
        yaml.safe_load(
            """
        from: foo
        name: test/foo
        version: 1.9
        """
        ),
        "foo",
    )

    module_a = Module(
        yaml.safe_load(
            """
        name: org.test.module.a
        version: 1.0
        """
        ),
        "path",
        "artifact_path",
    )

    module_b = Module(
        yaml.safe_load(
            """
        name: org.test.module.b
        version: 1.0
        """
        ),
        "path",
        "artifact_path",
    )

    module_registry = ModuleRegistry()
    module_registry.add_module(module_a)
    module_registry.add_module(module_b)

    resulting_install_list = OrderedDict()

    to_install_list = [
        Map({"name": "org.test.module.a", "version": "1.0"}),
        Map({"name": "org.test.module.b"}),
    ]

    image.process_install_list(
        image, to_install_list, resulting_install_list, module_registry
    )

    assert resulting_install_list == OrderedDict(
        [
            ("org.test.module.a", {"name": "org.test.module.a", "version": "1.0"}),
            ("org.test.module.b", {"name": "org.test.module.b"}),
        ]
    )


def test_module_processing_fail_when_no_modules_of_specified_name_can_be_found():
    image = Image(
        yaml.safe_load(
            """
        from: foo
        name: test/foo
        version: 1.9
        """
        ),
        "foo",
    )

    module_a = Module(
        yaml.safe_load(
            """
        name: org.test.module.a
        version: 1.0
        """
        ),
        "path",
        "artifact_path",
    )

    module_registry = ModuleRegistry()
    module_registry.add_module(module_a)

    resulting_install_list = OrderedDict()

    to_install_list = [
        Map({"name": "org.test.module.a", "version": "1.0"}),
        Map({"name": "org.test.module.b"}),
    ]

    with pytest.raises(CekitError) as excinfo:
        image.process_install_list(
            image, to_install_list, resulting_install_list, module_registry
        )

    assert "There are no modules with 'org.test.module.b' name available" in str(
        excinfo.value
    )


def test_module_processing_fail_when_module_not_found_for_specific_version():
    image = Image(
        yaml.safe_load(
            """
        from: foo
        name: test/foo
        version: 1.9
        """
        ),
        "foo",
    )

    module_a = Module(
        yaml.safe_load(
            """
        name: org.test.module.a
        version: 1.0
        """
        ),
        "path",
        "artifact_path",
    )

    module_registry = ModuleRegistry()
    module_registry.add_module(module_a)

    resulting_install_list = OrderedDict()

    to_install_list = [Map({"name": "org.test.module.a", "version": "1.1"})]

    with pytest.raises(CekitError) as excinfo:
        image.process_install_list(
            image, to_install_list, resulting_install_list, module_registry
        )

    assert (
        "Module 'org.test.module.a' with version '1.1' could not be found, available versions: 1.0"
        in str(excinfo.value)
    )


def test_module_processing_modules_with_multiple_versions(caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    image = Image(
        yaml.safe_load(
            """
        from: foo
        name: test/foo
        version: 1.9
        """
        ),
        "foo",
    )

    module_a = Module(
        yaml.safe_load(
            """
        name: org.test.module.a
        version: 1.0
        """
        ),
        "path",
        "artifact_path",
    )

    module_b = Module(
        yaml.safe_load(
            """
        name: org.test.module.b
        version: 1.0
        """
        ),
        "path",
        "artifact_path",
    )

    module_b_1 = Module(
        yaml.safe_load(
            """
        name: org.test.module.b
        version: 1.1
        """
        ),
        "path",
        "artifact_path",
    )

    module_registry = ModuleRegistry()
    module_registry.add_module(module_a)
    module_registry.add_module(module_b)
    module_registry.add_module(module_b_1)

    resulting_install_list = OrderedDict()

    to_install_list = [
        Map({"name": "org.test.module.a", "version": "1.0"}),
        Map({"name": "org.test.module.b"}),
    ]

    image.process_install_list(
        image, to_install_list, resulting_install_list, module_registry
    )

    assert resulting_install_list == OrderedDict(
        [
            ("org.test.module.a", {"name": "org.test.module.a", "version": "1.0"}),
            ("org.test.module.b", {"name": "org.test.module.b"}),
        ]
    )

    assert (
        "Module version not specified for 'org.test.module.b' module, using '1.1' default version"
        in caplog.text
    )


# https://github.com/cekit/cekit/issues/617
def test_module_processing_modules_with_single_versions(caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    image = Image(
        yaml.safe_load(
            """
        from: foo
        name: test/foo
        version: 1.9
        """
        ),
        "foo",
    )

    module_a = Module(
        yaml.safe_load(
            """
        name: org.test.module.a
        version: 1.0
        """
        ),
        "path",
        "artifact_path",
    )

    module_b = Module(
        yaml.safe_load(
            """
        name: org.test.module.b
        version: 1.0
        """
        ),
        "path",
        "artifact_path",
    )

    module_registry = ModuleRegistry()
    module_registry.add_module(module_a)
    module_registry.add_module(module_b)

    resulting_install_list = OrderedDict()

    to_install_list = [
        Map({"name": "org.test.module.a", "version": "1.0"}),
        Map({"name": "org.test.module.b"}),
    ]

    image.process_install_list(
        image, to_install_list, resulting_install_list, module_registry
    )

    assert resulting_install_list == OrderedDict(
        [
            ("org.test.module.a", {"name": "org.test.module.a", "version": "1.0"}),
            ("org.test.module.b", {"name": "org.test.module.b"}),
        ]
    )

    assert "Module version not specified for" not in caplog.text


def test_module_processing_fail_when_a_module_aready_exists_in_registry():
    module_a = Module(
        yaml.safe_load(
            """
        name: org.test.module.a
        version: 1.0
        """
        ),
        "path",
        "artifact_path",
    )

    module_a1 = Module(
        yaml.safe_load(
            """
        name: org.test.module.a
        version: 1.0
        """
        ),
        "path",
        "artifact_path",
    )

    module_registry = ModuleRegistry()
    module_registry.add_module(module_a)

    with pytest.raises(CekitError) as excinfo:
        module_registry.add_module(module_a1)

    assert (
        "Module 'org.test.module.a' with version '1.0' already exists in module registry"
        in str(excinfo.value)
    )


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_module_processing_warning_when_a_module_version_cannot_be_parsed_as_pep_440(
    caplog,
):
    caplog.set_level(logging.DEBUG, logger="cekit")

    module_a = Module(
        yaml.safe_load(
            """
        name: org.test.module.a
        version: 1.0
        """
        ),
        "path",
        "artifact_path",
    )

    module_a1 = Module(
        yaml.safe_load(
            """
        name: org.test.module.a
        version: aa fs df
        """
        ),
        "path",
        "artifact_path",
    )

    module_registry = ModuleRegistry()
    module_registry.add_module(module_a)
    module_registry.add_module(module_a1)

    assert (
        "Module's 'org.test.module.a' version 'aa fs df' does not follow PEP 440 versioning scheme (https://www.python.org/dev/peps/pep-0440)"
        in caplog.text
    )


def test_image_no_name():
    with pytest.raises(CekitError) as excinfo:
        Image(
            yaml.safe_load(
                """
        version: 1.9
        labels:
          - name: test
            value: val1
          - name: label2
            value: val2
        envs:
          - name: env1
            value: env1val
        """
            ),
            "foo",
        )

    assert "Cannot validate schema" in str(excinfo.value)
