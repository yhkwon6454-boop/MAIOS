from maios.config import MAIOSConfig


def test_config_create():
    config = MAIOSConfig()
    assert config is not None