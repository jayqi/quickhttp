import shutil
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
    run_timed_http_server,
    NoAvailablePortFound,
)

KEEP_ALIVE_TIME = 3  # Duration to keep server alive for
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
            "timeout": KEEP_ALIVE_TIME,
        },
        daemon=True,
    )
    thread.start()
    sleep(WAIT_TIME)
    yield (tmp_path, port)
    thread.join()


def test_version():
    assert isinstance(parse_version(__version__), Version)


def test_is_port_available(timed_http_server):
    _, port = timed_http_server
    assert not is_port_available(port)
    sleep(WAIT_TIME + KEEP_ALIVE_TIME)
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


def test_find_available_port_none_found(timed_http_server):
    directory, port = timed_http_server
    with pytest.raises(NoAvailablePortFound):
        find_available_port(range_min=port, range_max=port)


def test_run_timed_http_server(timed_http_server):
    directory, port = timed_http_server
    assert not is_port_available(port)
    response = requests.get(f"http://127.0.0.1:{port}")
    assert response.status_code == 200
    assert response.encoding == "utf-8"
    with (directory / "index.html").open("r") as fp:
        assert response.text == fp.read()
    sleep(WAIT_TIME + KEEP_ALIVE_TIME)
    assert is_port_available(port)
