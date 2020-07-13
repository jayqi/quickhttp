from pathlib import Path
import shutil
from functools import partial
from threading import Thread

from packaging.version import parse as parse_version, Version
import pytest
import requests

from quickhttp.core import (
    __version__,
    DEFAULT_PORT_RANGE_MIN,
    DEFAULT_PORT_RANGE_MAX,
    is_port_available,
    find_available_port,
    SearchType,
    working_directory,
    run_timed_http_server,
)


@pytest.fixture()
def timed_http_server(tmp_path, html_file):
    shutil.copy(html_file, tmp_path)
    port = find_available_port()
    run_server = partial(run_timed_http_server, port=port, directory=tmp_path, time=5)
    thread = Thread(target=run_server)
    thread.daemon = True
    thread.start()
    return (tmp_path, port)


def test_version():
    assert isinstance(parse_version(__version__), Version)


@pytest.mark.parametrize("search_type", [level.value for level in SearchType])
def test_find_available_port(search_type):
    port = find_available_port(search_type=search_type)
    assert is_port_available(port)
    assert port >= DEFAULT_PORT_RANGE_MIN
    assert port <= DEFAULT_PORT_RANGE_MAX


def test_run_timed_http_server(timed_http_server):
    directory, port = timed_http_server
    response = requests.get(f"http://0.0.0.0:{port}")
    assert response.status_code == 200
    with (directory / "index.html").open("r") as fp:
        assert response.text == fp.read()


def test_run_port_no_longer_available(timed_http_server):
    _, port = timed_http_server
    assert not is_port_available(port)


def test_working_directory(tmp_path):
    cwd = Path.cwd()
    assert cwd != tmp_path
    with working_directory(tmp_path):
        assert Path.cwd() == tmp_path
    assert Path.cwd() == cwd
