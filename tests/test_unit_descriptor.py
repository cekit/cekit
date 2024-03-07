import pytest
import yaml

from cekit.config import Config
from cekit.descriptor import Arg, Env, Image, Label, Osbs, Packages, Port, Volume
from cekit.errors import CekitError

config = Config()
config.configure("/dev/null", {"redhat": True})


def test_label():
    label = Label(
        yaml.safe_load(
            """
      name: "io.k8s.display-name"
      value: "JBoss A-MQ 6.2"
"""
        )
    )
    assert label["name"] == "io.k8s.display-name"
    assert label["value"] == "JBoss A-MQ 6.2"


def test_arg():
    arg = Arg(
        yaml.safe_load(
            """
      name: "io.k8s.display-name"
      value: "JBoss A-MQ 6.2"
"""
        )
    )
    assert arg.name == "io.k8s.display-name"
    assert arg.value == "JBoss A-MQ 6.2"

    arg = Arg(
        yaml.safe_load(
            """
        name: "QUARKUS_EXTENSIONS"
"""
        )
    )
    assert arg.name == "QUARKUS_EXTENSIONS"
    assert arg.value is None


def test_env():
    env = Env(
        yaml.safe_load(
            """
      name: "io.k8s.display-name"
      value: "JBoss A-MQ 6.2"
"""
        )
    )
    assert env["name"] == "io.k8s.display-name"
    assert env["value"] == "JBoss A-MQ 6.2"


def test_port():
    env = Port(
        yaml.safe_load(
            """
      value: 8788
      expose: False
"""
        )
    )
    assert env["value"] == 8788
    assert env["name"] == 8788
    assert not env["expose"]


def test_volume():
    volume = Volume(
        yaml.safe_load(
            """
    name: vol1
    path: /tmp/a
"""
        )
    )
    assert volume["name"] == "vol1"
    assert volume["path"] == "/tmp/a"


def test_volume_name():
    volume = Volume(
        yaml.safe_load(
            """
    path: /tmp/a
"""
        )
    )
    assert volume["name"] == "a"
    assert volume["path"] == "/tmp/a"


def test_osbs():
    osbs = Osbs(
        yaml.safe_load(
            """
    repository:
      name: foo
      branch: bar
"""
        ),
        "a/path/image.yaml",
    )

    assert osbs["repository"]["name"] == "foo"
    assert osbs["repository"]["branch"] == "bar"


def test_packages():
    pkg = Packages(
        yaml.safe_load(
            """
      install:
          - pkg-foo"""
        ),
        "a/path/image.yaml",
    )

    assert "pkg-foo" in pkg["install"]


def test_packages_invalid_old_repository_definition():
    with pytest.raises(CekitError, match=r"Cannot validate schema: Repository"):
        Packages(
            yaml.safe_load(
                """
        repositories:
            - repo-foo
            - repo-bar
        install:
            - pkg-foo"""
            ),
            "a/path/image.yaml",
        )


def test_packages_content_sets_and_content_sets_file():
    with pytest.raises(
        CekitError,
        match=r"You cannot specify 'content_sets' and 'content_sets_file' together in the packages section!",
    ):
        Packages(
            {
                "content_sets": {
                    "x86_64": ["rhel-server-rhscl-7-rpms", "rhel-7-server-rpms"]
                },
                "content_sets_file": "a_path.yaml",
            },
            "a/path",
        )


def test_packages_content_sets():
    pkg = Packages(
        {
            "content_sets": {
                "x86_64": ["rhel-server-rhscl-7-rpms", "rhel-7-server-rpms"]
            },
            "install": ["package_a", "package_b"],
        },
        "a/path",
    )

    assert "package_a" in pkg["install"]
    assert "content_sets_file" not in pkg


def test_packages_content_sets_file(mocker):
    with mocker.mock_module.patch(
        "cekit.descriptor.packages.os.path.exists"
    ) as exists_mock:
        exists_mock.return_value = True
        with mocker.mock_module.patch(
            "cekit.descriptor.packages.open", mocker.mock_open(read_data='{"a": 12}')
        ):
            pkg = Packages(
                {
                    "content_sets_file": "a_path.yaml",
                    "install": ["package_a", "package_b"],
                },
                "a/path",
            )

    assert "package_a" in pkg["install"]
    assert "content_sets_file" not in pkg
    assert pkg["content_sets"] == {"a": 12}


def test_image():
    image = Image(
        yaml.safe_load(
            """
    from: foo
    name: test/foo
    version: 1.9
    labels:
      - name: test
        value: val1
      - name: label2
        value: val2
    envs:
      - name: env1
        value: env1val
        required: false
        usage: build-time
    """
        ),
        "foo",
    )

    assert image["name"] == "test/foo"
    assert isinstance(image["labels"][0], Label)
    assert image["labels"][0]["name"] == "test"
    assert image["envs"][0]["required"] is False


def test_image_missing_name():
    with pytest.raises(CekitError):
        Image(
            yaml.safe_load(
                """
        from: foo
        version: 1.9"""
            ),
            "foo",
        )


def test_remove_none_key():
    image = Image(
        yaml.safe_load(
            """
    from: foo
    name: test/foo
    version: 1.9
    envs:
     - name: foo
       value: ~
    """
        ),
        "foo",
    )
    image.remove_none_keys()

    assert "envs" in image
    assert "value" not in image["envs"][0]


def test_image_artifacts(caplog):
    image = Image(
        yaml.safe_load(
            """
    from: foo
    name: test/foo
    version: 1.9
    labels:
      - name: test
        value: val1
      - name: label2
        value: val2
    artifacts:
      - url: https://archive.apache.org/dist/tomcat/tomcat-8/v8.5.24/bin/apache-tomcat-8.5.24.tar.gz
        md5: 080075877a66adf52b7f6d0013fa9730
      - path: /foo/bar
        md5: 080075877a66adf52b7f6d0013fa9730
    envs:
      - name: env1
        value: env1val
    """
        ),
        "foo",
    )

    assert image["name"] == "test/foo"
    assert isinstance(image["labels"][0], Label)
    assert image["labels"][0]["name"] == "test"
    assert (
        'No value found for \'name\' in \'{"dest": "/tmp/artifacts/", "md5": "080075877a66adf52b7f6d0013fa9730", "url": "https://archive.apache.org/dist/tomcat/tomcat-8/v8.5.24/bin/apache-tomcat-8.5.24.tar.gz"}\' artifact; using auto-generated value of \'apache-tomcat-8.5.24.tar.gz\''
        in caplog.text
    )
    assert (
        'No value found for \'name\' in \'{"dest": "/tmp/artifacts/", "md5": "080075877a66adf52b7f6d0013fa9730", "path": "/foo/bar"}\' artifact; using auto-generated value of \'bar\''
        in caplog.text
    )


def test_image_plain_artifacts_md5_fail(caplog):
    with pytest.raises(CekitError) as excinfo:
        Image(
            yaml.safe_load(
                """
            from: foo
            name: test/foo
            version: 1.9
            artifacts:
              - target: jolokia.jar
                md5: 080075877a66adf52b7f6d0013fa9730
            """
            ),
            "foo",
        )
    assert "Cannot validate schema: _PlainResource" in excinfo.value.message
    assert "Cannot find required key 'name'" in caplog.text


def test_image_plain_artifacts_md5():
    Image(
        yaml.safe_load(
            """
        from: foo
        name: test/foo
        version: 1.9
        artifacts:
          - name: jolokia.jar
            target: jolokia.jar
            md5: 080075877a66adf52b7f6d0013fa9730
        """
        ),
        "foo",
    )


def test_image_plain_artifacts_sha256():
    Image(
        yaml.safe_load(
            """
        from: foo
        name: test/foo
        version: 1.9
        artifacts:
          - name: jolokia.jar
            target: jolokia.jar
            sha256: ac8aef606f79c19321c9d74790168da973c4f10d2784e2e763d2bec8b4ac610f
        """
        ),
        "foo",
    )


def test_image_modules_git_repo(caplog):
    image = Image(
        yaml.safe_load(
            """
    from: foo
    name: test/foo
    version: 1.9
    modules:
        repositories:
            - git:
                url: "https://github.com/company/foobar-project-modules"
                ref: "release-3.1.0"
            - name: "another-module"
              git:
                url: "https://github.com/company/another-git-module"
                ref: "release-1.1"
        install:
            - name: "org.company.project.feature"
    """
        ),
        "foo",
    )

    assert image["name"] == "test/foo"
    assert (
        'No value found for \'name\' in \'{"git": {"ref": "release-3.1.0", "url": "https://github.com/company/foobar-project-modules"}}\' artifact; using auto-generated value of \'foobar-project-modules\''
        in caplog.text
    )


def test_image_descriptor_with_execute():
    with pytest.raises(CekitError) as excinfo:
        Image(
            yaml.safe_load(
                """
        from: foo
        name: test/foo
        version: 1.9
        execute:
              - script: build.sh
        """
            ),
            "foo",
        )

    assert "Cannot validate schema: Image" in excinfo.value.message


def test_image_pnc_artifacts_1():
    image = Image(
        yaml.safe_load(
            """
            from: foo
            name: test/foo
            version: 1.9
            artifacts:
              - name: foobar
                target: jolokia.jar
                pnc_artifact_id: '12345'
                pnc_build_id: '54321'
            """
        ),
        "foo",
    )
    assert image.artifacts[0]["name"] == "foobar"
    assert image.artifacts[0]["pnc_build_id"] == "54321"
    assert image.artifacts[0]["target"] == "jolokia.jar"
    assert image.artifacts[0]["dest"] == "/tmp/artifacts/"


def test_image_pnc_artifacts_2():
    image = Image(
        yaml.safe_load(
            """
            from: foo
            name: test/foo
            version: 1.9
            artifacts:
              - target: jolokia.jar
                dest: '/installation/'
                pnc_artifact_id: '12345'
                pnc_build_id: '54321'
            """
        ),
        "foo",
    )
    print(f"Got {image.artifacts[0]}")
    assert image.artifacts[0]["name"] == "jolokia.jar"
    assert image.artifacts[0]["pnc_build_id"] == "54321"
    assert image.artifacts[0]["target"] == "jolokia.jar"
    assert image.artifacts[0]["dest"] == "/installation/"


def test_image_follow_tag():
    image = Image(
        yaml.safe_load(
            """
    from: foo:latest
    name: test/foo
    follow_tag: registry.fedoraproject.org/flatpak-build-base
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

    assert image["name"] == "test/foo"
    assert isinstance(image["labels"][0], Label)
    assert image["labels"][0]["name"] == "test"
