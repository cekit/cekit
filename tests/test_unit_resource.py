import logging
import os
from urllib.request import Request

import pytest
import yaml

from cekit.config import Config
from cekit.descriptor import Image, Overrides
from cekit.descriptor.resource import create_resource
from cekit.errors import CekitError

try:
    from unittest.mock import call
except ImportError:
    from mock import call

config = Config()


def setup_function(function):
    config.cfg["common"] = {"work_dir": "/tmp"}

    if os.path.exists("file"):
        os.remove("file")


def test_repository_dir_is_constructed_properly(mocker):
    mocker.patch("subprocess.run")
    mocker.patch("os.path.isdir", ret="True")
    mocker.patch("cekit.descriptor.resource.Chdir", autospec=True)

    res = create_resource(
        {"git": {"url": "http://host.com/url/repo.git", "ref": "ref"}}
    )

    assert res.copy("dir") == "dir/repo"


def test_repository_dir_uses_name_if_defined(mocker):
    mocker.patch("subprocess.run")
    mocker.patch("os.path.isdir", ret="True")
    mocker.patch("cekit.descriptor.resource.Chdir", autospec=True)

    res = create_resource(
        {
            "name": "some-id",
            "git": {"url": "http://host.com/url/repo.git", "ref": "ref"},
        }
    )
    assert res.copy("dir") == "dir/some-id"


def test_repository_dir_uses_target_if_defined(mocker):
    mocker.patch("subprocess.run")
    mocker.patch("os.path.isdir", ret="True")
    mocker.patch("cekit.descriptor.resource.Chdir", autospec=True)

    res = create_resource(
        {
            "target": "some-name",
            "git": {"url": "http://host.com/url/repo.git", "ref": "ref"},
        }
    )
    assert res.copy("dir") == "dir/some-name"


def test_git_clone(mocker):
    mock = mocker.patch("subprocess.run")
    mocker.patch("os.path.isdir", ret="True")
    mocker.patch("cekit.descriptor.resource.Chdir", autospec=True)

    res = create_resource(
        {"git": {"url": "http://host.com/url/path.git", "ref": "ref"}}
    )
    res.copy("dir")
    mock.assert_has_calls(
        [
            call(
                ["git", "clone", "http://host.com/url/path.git", "dir/path"],
                stdout=None,
                stderr=None,
                check=True,
                universal_newlines=True,
            ),
            call(
                ["git", "checkout", "ref"],
                stdout=None,
                stderr=None,
                check=True,
                universal_newlines=True,
            ),
        ],
        any_order=True,
    )


def get_res(mocker):
    res = mocker.Mock()
    res.status_code = 200
    res.iter_content = lambda chunk_size: [b"test"]
    return res


def get_ctx(mocker):
    ctx = mocker.Mock()
    ctx.check_hostname = True
    ctx.verify_mode = 1
    return ctx


def get_mock_urlopen(mocker):
    return mocker.patch("cekit.tools.urlopen", return_value=get_res(mocker))


def get_mock_ssl(mocker, ctx):
    return mocker.patch("cekit.tools.ssl.create_default_context", return_value=ctx)


def test_fetching_with_ssl_verify(mocker):
    config.cfg["common"]["ssl_verify"] = True
    ctx = get_ctx(mocker)
    get_mock_ssl(mocker, ctx)
    mock_urlopen = get_mock_urlopen(mocker)

    res = create_resource({"name": "file", "url": "https://dummy"})

    try:
        res.copy()
    except Exception:
        pass

    request: Request = mock_urlopen.call_args[0][0]
    mock_urlopen.assert_called_with(request, context=ctx)
    assert request.get_full_url() == "https://dummy"
    assert ctx.check_hostname is True
    assert ctx.verify_mode == 1


def test_fetching_disable_ssl_verify(mocker):
    config.cfg["common"]["ssl_verify"] = False

    mock_urlopen = get_mock_urlopen(mocker)
    ctx = get_ctx(mocker)
    get_mock_ssl(mocker, ctx)

    res = create_resource({"name": "file", "url": "https://dummy"})

    try:
        res.copy()
    except Exception:
        pass

    request: Request = mock_urlopen.call_args[0][0]
    mock_urlopen.assert_called_with(request, context=ctx)
    assert request.get_full_url() == "https://dummy"

    assert ctx.check_hostname is False
    assert ctx.verify_mode == 0


def test_fetching_bad_status_code():
    res = create_resource({"name": "file", "url": "http://dummy"})
    with pytest.raises(CekitError):
        res.copy()


def test_fetching_file_exists_but_used_as_is(mocker):
    """
    It should not download the file, because we didn't
    specify any hash algorithm, so integrity checking is
    implicitly disabled here.
    """
    with open("file", "w") as f:  # noqa: F841
        pass
    mock_urlopen = get_mock_urlopen(mocker)
    res = create_resource(
        {
            "name": "file",
            "url": "http://dummy",
            "md5": "d41d8cd98f00b204e9800998ecf8427e",
        }
    )
    res.copy()
    mock_urlopen.assert_not_called()


def test_fetching_file_exists_fetched_again(mocker):
    """
    It should download the file again, because available
    file locally doesn't match checksum.
    """
    mock_urlopen = get_mock_urlopen(mocker)
    ctx = get_ctx(mocker)
    get_mock_ssl(mocker, ctx)

    with open("file", "w") as f:  # noqa: F841
        pass
    res = create_resource({"name": "file", "url": "http://dummy", "md5": "123456"})
    with pytest.raises(CekitError):
        # Checksum will fail, because the "downloaded" file
        # will not have md5 equal to 123456. We need investigate
        # mocking of requests get calls to do it properly
        res.copy()
    request: Request = mock_urlopen.call_args[0][0]
    mock_urlopen.assert_called_with(request, context=ctx)
    assert request.get_full_url() == "http://dummy"


def test_fetching_file_exists_no_hash_fetched_again(mocker):
    """
    It should download the file again, because available
    file locally doesn't match checksum.
    """
    mock_urlopen = get_mock_urlopen(mocker)
    ctx = get_ctx(mocker)
    get_mock_ssl(mocker, ctx)

    with open("file", "w") as f:  # noqa: F841
        pass

    res = create_resource({"name": "file", "url": "http://dummy"})

    with pytest.raises(CekitError):
        # url is not valid so we get error, but we are not interested
        # in it. We just need to check that we attempted to downlad.
        res.copy()
    request: Request = mock_urlopen.call_args[0][0]
    mock_urlopen.assert_called_with(request, context=ctx)
    assert request.get_full_url() == "http://dummy"


def test_generated_url_without_cacher():
    res = create_resource({"url": "url"})
    assert res._Resource__substitute_cache_url("url") == "url"


def test_resource_verify(mocker):
    mock = mocker.patch("cekit.descriptor.resource.check_sum")
    res = create_resource({"url": "dummy", "sha256": "justamocksum"})
    res._Resource__verify("dummy")
    mock.assert_called_with("dummy", "sha256", "justamocksum")


def test_generated_url_with_cacher():
    config.cfg["common"]["cache_url"] = "#filename#,#algorithm#,#hash#"
    res = create_resource({"url": "dummy", "sha256": "justamocksum"})
    res.name = "file"
    assert res._Resource__substitute_cache_url("file") == "file,sha256,justamocksum"


def test_path_resource_absolute():
    res = create_resource({"name": "foo", "path": "/bar"}, directory="/foo")
    assert res.path == "/bar"


def test_path_resource_relative():
    res = create_resource({"name": "foo", "path": "bar"}, directory="/foo")
    assert res.path == "/foo/bar"


def test_path_local_existing_resource_no_cacher_use(mocker):
    config.cfg["common"]["cache_url"] = "#filename#,#algorithm#,#hash#"
    mocker.patch("os.path.exists", return_value=True)
    shutil_mock = mocker.patch("shutil.copy2")

    res = create_resource({"name": "foo", "path": "bar"}, directory="/foo")

    mocker.spy(res, "_download_file")

    res.guarded_copy("target")

    shutil_mock.assert_called_with("/foo/bar", "target")
    assert res._download_file.call_count == 0


def test_path_local_non_existing_resource_with_cacher_use(mocker):
    config.cfg["common"]["cache_url"] = "#filename#,#algorithm#,#hash#"
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch("os.makedirs")

    res = create_resource({"name": "foo", "path": "bar"}, directory="/foo")

    mocker.spy(res, "_download_file")
    download_file_mock = mocker.patch.object(res, "_download_file")

    res.guarded_copy("target")

    download_file_mock.assert_called_with("/foo/bar", "target")


def test_url_resource_download_cleanup_after_failure(mocker, tmpdir, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("os.path.exists", return_value=False)
    mocker.patch("os.makedirs")
    os_remove_mock = mocker.patch("os.remove")

    urlopen_class_mock = mocker.patch("cekit.tools.urlopen")
    urlopen_mock = urlopen_class_mock.return_value
    urlopen_mock.getcode.return_value = 200
    urlopen_mock.read.side_effect = Exception

    res = create_resource({"url": "http://server.org/dummy", "sha256": "justamocksum"})

    targetfile = os.path.join(str(tmpdir), "targetfile")

    with pytest.raises(CekitError) as excinfo:
        res.guarded_copy(targetfile)

    assert "Error copying resource: 'dummy'. See logs for more info" in str(
        excinfo.value
    )
    assert f"Removing incompletely downloaded '{targetfile}' file" in caplog.text

    request: Request = urlopen_class_mock.call_args[0][0]
    urlopen_class_mock.assert_called_with(request, context=mocker.ANY)
    assert request.get_full_url() == "http://server.org/dummy"
    os_remove_mock.assert_called_with(targetfile)


def test_copy_plain_resource_with_cacher(mocker, tmpdir):
    config.cfg["common"]["cache_url"] = "#filename#,#algorithm#,#hash#"
    config.cfg["common"]["work_dir"] = str(tmpdir)

    urlopen_class_mock = mocker.patch("cekit.tools.urlopen")
    mock_urlopen = urlopen_class_mock.return_value
    mock_urlopen.getcode.return_value = 200
    mock_urlopen.read.side_effect = [b"one", b"two", None]

    ctx = get_ctx(mocker)
    get_mock_ssl(mocker, ctx)

    with open("file", "w") as f:  # noqa: F841
        pass

    res = create_resource({"name": "foo", "md5": "5b9164ad6f496d9dee12ec7634ce253f"})

    substitute_cache_url_mock = mocker.patch.object(
        res, "_Resource__substitute_cache_url", return_value="http://cache/abc"
    )

    res.copy(str(tmpdir))

    substitute_cache_url_mock.assert_called_once_with(None)
    request: Request = urlopen_class_mock.call_args[0][0]
    urlopen_class_mock.assert_called_with(request, context=ctx)
    assert request.get_full_url() == "http://cache/abc"


def test_copy_plain_resource_from_brew(mocker, tmpdir):
    config.cfg["common"]["work_dir"] = str(tmpdir)
    config.cfg["common"]["redhat"] = True

    urlopen_class_mock = mocker.patch("cekit.tools.urlopen")
    mock_urlopen = urlopen_class_mock.return_value
    mock_urlopen.getcode.return_value = 200
    mock_urlopen.read.side_effect = [b"one", b"two", None]

    ctx = get_ctx(mocker)
    get_mock_ssl(mocker, ctx)

    with open("file", "w") as f:  # noqa: F841
        pass

    res = create_resource({"name": "foo", "md5": "5b9164ad6f496d9dee12ec7634ce253f"})

    mocker.spy(res, "_Resource__substitute_cache_url")

    mock_get_brew_url = mocker.patch(
        "cekit.descriptor.resource.get_brew_url", return_value="http://cache/abc"
    )

    res.copy(str(tmpdir))

    mock_get_brew_url.assert_called_once_with("5b9164ad6f496d9dee12ec7634ce253f")
    assert res._Resource__substitute_cache_url.call_count == 0
    request: Request = urlopen_class_mock.call_args[0][0]
    urlopen_class_mock.assert_called_with(request, context=ctx)
    assert request.get_full_url() == "http://cache/abc"


def test_override_resource_remove_chksum():
    image = Image(
        yaml.safe_load(
            """
    from: foo
    name: test/foo
    version: 1.9
    artifacts:
      - name: abs
        path: /tmp/abs
        md5: 'foo'
        sha1: 'foo'
        sha256: 'foo'
        sha512: 'foo'
    """
        ),
        "foo",
    )
    overrides = Overrides(
        yaml.safe_load(
            """
    artifacts:
      - name: abs
        path: /tmp/over
"""
        ),
        "foo",
    )
    overrides.merge(image)

    assert overrides["from"] == "foo"
    assert overrides["artifacts"][0]["path"] == "/tmp/over"
    assert "md5" not in overrides["artifacts"][0]
    assert "sha1" not in overrides["artifacts"][0]
    assert "sha256" not in overrides["artifacts"][0]
    assert "sha512" not in overrides["artifacts"][0]


def test_fetching_file_with_authentication(mocker):
    """
    It should download the file again, because available
    file locally doesn't match checksum.
    """
    mock_urlopen = get_mock_urlopen(mocker)
    config.cfg["common"]["url_authentication"] = "dummy.com#username:password"
    ctx = get_ctx(mocker)
    get_mock_ssl(mocker, ctx)

    with open("file", "w") as f:  # noqa: F841
        pass
    res = create_resource({"name": "file", "url": "http://dummy.com", "md5": "123456"})
    with pytest.raises(CekitError):
        # Checksum will fail, because the "downloaded" file
        # will not have md5 equal to 123456. We need investigate
        # mocking of requests get calls to do it properly
        res.copy()
    request: Request = mock_urlopen.call_args[0][0]
    mock_urlopen.assert_called_with(request, context=ctx)
    assert request.get_full_url() == "http://dummy.com"
    assert request.get_header("Authorization") == "Basic dXNlcm5hbWU6cGFzc3dvcmQ="
