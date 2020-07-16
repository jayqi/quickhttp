from pathlib import Path
import shutil
from functools import partial
from threading import Thread
from time import sleep

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
    NoAvailablePortFound,
)

KEEP_ALIVE_TIME = 4  # Duration to keep server alive for
WAIT_TIME = 2  # Duration to wait before running test, to give server time to start up


@pytest.fixture()
def timed_http_server(tmp_path, html_file):
    shutil.copy(html_file, tmp_path)
    port = find_available_port()
    thread = Thread(
        target=run_timed_http_server,
        kwargs={
            "address": "127.0.0.1",
            "port": port,
            "directory": tmp_path,
            "time": KEEP_ALIVE_TIME,
        },
    )
    thread.daemon = True
    thread.start()
    sleep(WAIT_TIME)
    return (tmp_path, port)


def test_version():
    assert isinstance(parse_version(__version__), Version)


def test_is_port_available(timed_http_server):
    _, port = timed_http_server
    assert not is_port_available(port)
    sleep(KEEP_ALIVE_TIME)
    assert is_port_available(port)


@pytest.mark.parametrize("search_type", [level.value for level in SearchType])
def test_find_available_port(search_type):
    port = find_available_port(search_type=search_type)
    assert is_port_available(port)
    assert port >= DEFAULT_PORT_RANGE_MIN
    assert port <= DEFAULT_PORT_RANGE_MAX


def test_find_available_port_invalid_search_type():
    with pytest.raises(ValueError, match="Invalid search_type"):
        find_available_port(search_type="invalid_type")


def test_run_timed_http_server(timed_http_server):
    directory, port = timed_http_server
    assert not is_port_available(port)
    response = requests.get(f"http://127.0.0.1:{port}")
    assert response.status_code == 200
    with (directory / "index.html").open("r") as fp:
        assert response.text == fp.read()
    sleep(6)
    assert is_port_available(port)


def test_working_directory(tmp_path):
    cwd = Path.cwd()
    assert cwd != tmp_path
    with working_directory(tmp_path):
        assert Path.cwd() == tmp_path
    assert Path.cwd() == cwd
