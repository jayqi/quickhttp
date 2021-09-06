from packaging.version import parse as parse_version, Version

from quickhttp._version import __version__


def test_version():
    assert isinstance(parse_version(__version__), Version)
