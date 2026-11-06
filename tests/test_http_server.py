from contextlib import contextmanager
import shutil
import socket
from threading import Thread
import time
from time import sleep

import pytest
import requests

import quickhttp.exceptions as exceptions
from quickhttp.http_server import (
    DEFAULT_PORT_RANGE_MAX,
    DEFAULT_PORT_RANGE_MIN,
    QuickHTTPServer,
    SearchType,
    create_server,
    find_available_port,
    is_port_available,
    run_timed_http_server,
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
    with pytest.raises(exceptions.InvalidSearchTypeError, match="Invalid search_type"):
        find_available_port(search_type="invalid_type")


def test_find_available_port_none_found(timed_http_server):
    directory, port = timed_http_server
    with pytest.raises(exceptions.NoAvailablePortFoundError):
        find_available_port(range_min=port, range_max=port)


def test_run_timed_http_server(timed_http_server):
    # Server is working
    directory, port = timed_http_server
    assert not is_port_available(port)
    response = requests.get(f"http://127.0.0.1:{port}")
    assert response.status_code == 200
    with (directory / "index.html").open("r") as fp:
        assert response.text == fp.read()

    sleep(WAIT_TIME + KEEP_ALIVE_TIME)

    # Server is closed
    assert is_port_available(port)
    with pytest.raises(requests.exceptions.ConnectionError):
        requests.get(f"http://127.0.0.1:{port}")


@contextmanager
def held_port(host: str = "127.0.0.1", port: int = 0):
    """Listen on a port with a plain socket, as an unrelated program would."""
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        sock.bind((host, port))
        sock.listen()
        yield sock.getsockname()[1]


def free_port_pair(host: str = "127.0.0.1") -> int:
    """Return a port N such that N and N + 1 are both free on host."""
    for _ in range(50):
        with held_port(host) as port:
            pass
        try:
            with held_port(host, port), held_port(host, port + 1):
                return port
        except OSError:
            continue
    raise RuntimeError("Unable to find two consecutive free ports.")


@contextmanager
def serving(server: QuickHTTPServer, idle_timeout: float = 1):
    """Run serve_until_idle in a background thread and wait for it to return on exit."""
    thread = Thread(target=server.serve_until_idle, args=(idle_timeout,), daemon=True)
    with server:
        thread.start()
        yield thread
        thread.join(timeout=idle_timeout + 5)
        assert not thread.is_alive()


def test_create_server_binds_first_free_port_in_range(tmp_path):
    port = free_port_pair()
    with held_port(port=port):
        with create_server(tmp_path, port_range=(port, port + 1)) as server:
            assert server.port == port + 1


def test_create_server_falls_back_to_os_port_when_range_is_taken(tmp_path):
    port = free_port_pair()
    with held_port(port=port), held_port(port=port + 1):
        with create_server(tmp_path, port_range=(port, port + 1)) as server:
            assert server.port not in (0, port, port + 1)


@pytest.mark.parametrize("port_range", [(9000, 8000), (0, 10), (65535, 65536)])
def test_create_server_invalid_port_range(tmp_path, port_range):
    with pytest.raises(exceptions.InvalidPortRangeError, match="Invalid port range"):
        create_server(tmp_path, port_range=port_range)


def test_create_server_explicit_port_in_use(tmp_path):
    with held_port() as port:
        with pytest.raises(OSError):
            create_server(tmp_path, port=port)


def test_create_server_os_chosen_port(tmp_path):
    with create_server(tmp_path, port=0) as server:
        assert server.port > 0
        assert server.url == f"http://127.0.0.1:{server.port}/"


def test_create_server_unresolvable_address(tmp_path):
    with pytest.raises(socket.gaierror):
        create_server(tmp_path, bind="nonexistent.invalid")


@pytest.mark.skipif(not socket.has_ipv6, reason="IPv6 not available")
def test_create_server_skips_port_in_use_on_loopback_sibling(tmp_path):
    port = free_port_pair()
    with held_port("::1", port):
        with create_server(tmp_path, port_range=(port, port + 1)) as server:
            assert server.port == port + 1


def test_server_serves_file_and_listing(tmp_path, html_file):
    shutil.copy(html_file, tmp_path)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "data.txt").write_text("data")
    server = create_server(tmp_path, port=0)
    with serving(server):
        response = requests.get(server.url, timeout=5)
        assert response.status_code == 200
        assert response.text == html_file.read_text()
        assert response.headers["Cache-Control"] == "no-cache"

        listing = requests.get(server.url + "sub/", timeout=5)
        assert listing.status_code == 200
        assert "data.txt" in listing.text


def test_server_idle_connection_does_not_block_requests(tmp_path, html_file):
    shutil.copy(html_file, tmp_path)
    server = create_server(tmp_path, port=0)
    with serving(server), socket.create_connection(("127.0.0.1", server.port)):
        response = requests.get(server.url, timeout=5)
        assert response.status_code == 200


def test_server_shuts_down_when_idle_despite_idle_connection(tmp_path):
    server = create_server(tmp_path, port=0)
    start = time.monotonic()
    with serving(server, idle_timeout=0.5), socket.create_connection(("127.0.0.1", server.port)):
        requests.get(server.url, timeout=5)
    assert time.monotonic() - start < 3


def test_server_does_not_shut_down_while_request_in_progress(tmp_path):
    server = create_server(tmp_path, port=0)
    with serving(server, idle_timeout=0.5) as thread:
        with server.track_request():
            time.sleep(1.5)
            assert thread.is_alive()
        request_ended = time.monotonic()
    assert time.monotonic() - request_ended >= 0.4


@pytest.mark.skipif(not socket.has_ipv6, reason="IPv6 not available")
def test_server_ipv6_loopback(tmp_path):
    server = create_server(tmp_path, bind="::1", port=0)
    assert server.url == f"http://[::1]:{server.port}/"
    with serving(server):
        assert requests.get(server.url, timeout=5).status_code == 200


@pytest.mark.skipif(not socket.has_dualstack_ipv6(), reason="Dual-stack IPv6 not available")
def test_server_dual_stack_accepts_ipv4(tmp_path):
    server = create_server(tmp_path, bind="::", port=0)
    with serving(server):
        assert requests.get(f"http://127.0.0.1:{server.port}/", timeout=5).status_code == 200
