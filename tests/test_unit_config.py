import pytest

from cekit.config import Config


def test_config_key_not_available():
    config = Config()
    config.configure("/dev/null", {})

    with pytest.raises(KeyError) as e_info:
        config.get("not_exists", "key")
        assert e_info == "'/not_exists' section doesn't exists in Cekit configuration!"


def test_config_key_exists():
    config = Config()
    config.configure("/dev/null", {})

    assert not config.get("common", "redhat")
