from packaging.version import Version
from packaging.version import parse as parse_version

from quickhttp import __version__


def test_version():
    assert isinstance(parse_version(__version__), Version)
