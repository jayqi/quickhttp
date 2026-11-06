from contextlib import contextmanager
import shutil
import socket
from threading import Event, Thread
import time

import pytest
import requests

from helpers import free_port_pair, held_port
import quickhttp.exceptions as exceptions
from quickhttp.http_server import QuickHTTPServer, _Handler, create_server

requires_ipv6 = pytest.mark.skipif(not socket.has_ipv6, reason="IPv6 not available")
requires_dualstack = pytest.mark.skipif(
    not socket.has_dualstack_ipv6(), reason="Dual-stack IPv6 not available"
)
OTHER_ADDRESS_CASES = [
    pytest.param("127.0.0.1", "0.0.0.0", None, id="all-ipv4"),
    pytest.param("127.0.0.1", "::", False, id="all-dualstack", marks=requires_dualstack),
    pytest.param("127.0.0.1", "::", True, id="all-ipv6", marks=requires_ipv6),
    pytest.param("127.0.0.1", "::1", None, id="loopback-ipv6", marks=requires_ipv6),
    pytest.param("::1", "127.0.0.1", None, id="loopback-ipv4", marks=requires_ipv6),
    pytest.param("::", "127.0.0.1", None, id="bind-all", marks=requires_dualstack),
]


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


@pytest.mark.parametrize("bind, held_host, v6only", OTHER_ADDRESS_CASES)
def test_create_server_skips_port_in_use_on_other_address(tmp_path, bind, held_host, v6only):
    port = free_port_pair()
    with held_port(held_host, port, v6only=v6only):
        with create_server(tmp_path, bind=bind, port_range=(port, port + 1)) as server:
            assert server.port == port + 1


def test_create_server_reuses_port_after_serving(tmp_path):
    server = create_server(tmp_path, port=0)
    port = server.port
    with serving(server, idle_timeout=0.5):
        requests.get(server.url, timeout=5)
    with create_server(tmp_path, port_range=(port, port)) as server:
        assert server.port == port


@pytest.mark.parametrize("port_range", [(9000, 8000), (0, 10), (65535, 65536)])
def test_create_server_invalid_port_range(tmp_path, port_range):
    with pytest.raises(exceptions.InvalidPortRangeError, match="Invalid port range"):
        create_server(tmp_path, port_range=port_range)


@pytest.mark.parametrize("port", [-1, 65536])
def test_create_server_invalid_port(tmp_path, port):
    with pytest.raises(exceptions.InvalidPortError, match=f"Invalid port {port}."):
        create_server(tmp_path, port=port)


def test_create_server_explicit_port_in_use(tmp_path):
    with held_port() as port:
        with pytest.raises(OSError):
            create_server(tmp_path, port=port)


@pytest.mark.parametrize("bind, held_host, v6only", OTHER_ADDRESS_CASES)
def test_create_server_explicit_port_in_use_on_other_address(tmp_path, bind, held_host, v6only):
    with held_port(held_host, v6only=v6only) as port:
        with pytest.raises(OSError, match="Address already in use"):
            create_server(tmp_path, bind=bind, port=port)


def test_create_server_os_chosen_port(tmp_path):
    with create_server(tmp_path, port=0) as server:
        assert server.port > 0
        assert server.url == f"http://127.0.0.1:{server.port}/"


def test_create_server_does_not_look_up_hostname(tmp_path, monkeypatch):
    def fail_getfqdn(name=""):
        raise AssertionError("getfqdn called")

    monkeypatch.setattr(socket, "getfqdn", fail_getfqdn)
    with create_server(tmp_path, port=0) as server:
        assert server.server_name == "127.0.0.1"
        assert server.server_port == server.port


def test_create_server_unresolvable_address(tmp_path):
    with pytest.raises(socket.gaierror):
        create_server(tmp_path, bind="nonexistent.invalid")


def test_server_serves_file_and_listing(tmp_path, html_file):
    shutil.copy(html_file, tmp_path)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "data.txt").write_text("data")
    server = create_server(tmp_path, port=0)
    with serving(server):
        response = requests.get(server.url, timeout=5)
        assert response.status_code == 200
        assert response.text == html_file.read_text()
        assert response.headers["Cache-Control"] == "no-store"

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
    with socket.create_connection(("127.0.0.1", server.port)):
        start = time.monotonic()
        with serving(server, idle_timeout=0.5):
            requests.get(server.url, timeout=5)
        assert time.monotonic() - start < 3


def test_server_requests_restart_idle_timeout(tmp_path):
    server = create_server(tmp_path, port=0)
    with serving(server, idle_timeout=1) as thread:
        for _ in range(4):
            time.sleep(0.5)
            requests.get(server.url, timeout=5)
        assert thread.is_alive()
        last_request = time.monotonic()
    assert time.monotonic() - last_request >= 0.9


def test_server_does_not_shut_down_while_request_in_progress(tmp_path, monkeypatch):
    (tmp_path / "data.txt").write_text("data")
    copy_started = Event()
    release_copy = Event()
    original_copyfile = _Handler.copyfile

    def blocking_copyfile(self, source, outputfile):
        copy_started.set()
        release_copy.wait(timeout=10)
        original_copyfile(self, source, outputfile)

    monkeypatch.setattr(_Handler, "copyfile", blocking_copyfile)
    server = create_server(tmp_path, port=0)
    with serving(server, idle_timeout=0.5) as thread:
        request = Thread(target=requests.get, args=(server.url + "data.txt",), daemon=True)
        request.start()
        assert copy_started.wait(timeout=5)
        time.sleep(1.5)
        assert thread.is_alive()
        release_copy.set()
        request.join(timeout=5)
        request_ended = time.monotonic()
    assert time.monotonic() - request_ended >= 0.4


@requires_ipv6
def test_server_ipv6_loopback(tmp_path):
    server = create_server(tmp_path, bind="::1", port=0)
    assert server.url == f"http://[::1]:{server.port}/"
    with serving(server):
        assert requests.get(server.url, timeout=5).status_code == 200


@requires_dualstack
def test_server_dual_stack_accepts_ipv4(tmp_path):
    server = create_server(tmp_path, bind="::", port=0)
    with serving(server):
        assert requests.get(f"http://127.0.0.1:{server.port}/", timeout=5).status_code == 200
