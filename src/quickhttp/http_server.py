from collections.abc import Generator
from contextlib import contextmanager, suppress
import errno
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
import socket
import socketserver
import threading
import time
from typing import cast

from quickhttp.exceptions import InvalidPortError, InvalidPortRangeError

DEFAULT_PORT_RANGE_MIN: int = 8000
"""Default minimum of the port search range."""
DEFAULT_PORT_RANGE_MAX: int = 8999
"""Default maximum of the port search range."""

_SKIPPABLE_BIND_ERRNOS = frozenset(
    code
    for name in ("EADDRINUSE", "EACCES", "WSAEADDRINUSE", "WSAEACCES")
    if (code := getattr(errno, name, None)) is not None
)
"""Bind errors that mean a port is in use or not permitted, as opposed to a bad address."""

_CONFLICT_PROBE_HOSTS = ("127.0.0.1", "::1", "0.0.0.0", "::")
"""Addresses where a port in use makes it unavailable. They're probed separately because on macOS,
SO_REUSEADDR allows binding a specific address while another socket listens on the wildcard, and
vice versa."""


def _set_bind_options(sock: socket.socket) -> None:
    # On Windows, SO_REUSEADDR allows binding a port that another socket is listening on.
    if os.name == "nt":
        sock.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE"), 1)
    else:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


class _Handler(SimpleHTTPRequestHandler):
    timeout = 60

    def do_GET(self):
        with self._server()._track_request():
            super().do_GET()

    def do_HEAD(self):
        with self._server()._track_request():
            super().do_HEAD()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _server(self) -> "QuickHTTPServer":
        assert isinstance(self.server, QuickHTTPServer)
        return self.server


class QuickHTTPServer(ThreadingHTTPServer):
    """Subclass of
    [`http.server.ThreadingHTTPServer`](https://docs.python.org/3/library/http.server.html)
    that serves a directory, supports IPv4 and IPv6 addresses, and shuts down when idle.
    Use [`create_server`][quickhttp.http_server.create_server] to create one with automatic
    port selection.

    Args:
        server_address (tuple[str, int]): Address and port to bind to. The address can be a
            hostname or an IPv4 or IPv6 address. `"::"` also accepts IPv4 connections where
            the platform supports it.
        directory (str | os.PathLike[str]): Directory to serve.
    """

    allow_reuse_address = False  # _set_bind_options sets this per platform

    def __init__(self, server_address: tuple[str, int], directory: str | os.PathLike[str]):
        host, port = server_address
        family, _, _, _, sockaddr = socket.getaddrinfo(
            host, port, type=socket.SOCK_STREAM, flags=socket.AI_PASSIVE
        )[0]
        self.address_family = family
        self._lock = threading.Lock()
        self._in_flight = 0
        self._last_activity = time.monotonic()
        super().__init__(
            cast("tuple[str, int] | tuple[str, int, int, int]", sockaddr),
            partial(_Handler, directory=os.fspath(directory)),
        )

    def server_bind(self):
        if self.address_family == socket.AF_INET6:
            with suppress(OSError):
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        _set_bind_options(self.socket)
        # Skips HTTPServer.server_bind, whose reverse DNS lookup for server_name can hang.
        socketserver.TCPServer.server_bind(self)
        self.server_name = self.host
        self.server_port = self.port

    @property
    def host(self) -> str:
        """Address the server is bound to."""
        return str(self.server_address[0])

    @property
    def port(self) -> int:
        """Port the server is bound to."""
        return int(self.server_address[1])

    @property
    def url(self) -> str:
        """URL of the served directory."""
        host = f"[{self.host}]" if self.address_family == socket.AF_INET6 else self.host
        return f"http://{host}:{self.port}/"

    @contextmanager
    def _track_request(self) -> Generator[None, None, None]:
        """Mark a request as in progress. The server doesn't count as idle while any request
        is in progress, and the idle time restarts when the last one finishes.
        """
        with self._lock:
            self._in_flight += 1
            self._last_activity = time.monotonic()
        try:
            yield
        finally:
            with self._lock:
                self._in_flight -= 1
                self._last_activity = time.monotonic()

    def _idle_seconds(self) -> float:
        with self._lock:
            if self._in_flight:
                return 0.0
            return time.monotonic() - self._last_activity

    def serve_until_idle(self, idle_timeout: float) -> None:
        """Serve requests until no request has been in progress for `idle_timeout` seconds.
        The server is shut down on return, including when interrupted by an exception such
        as `KeyboardInterrupt`.

        Args:
            idle_timeout (float): Seconds without requests after which to shut down.
        """
        with self._lock:
            self._last_activity = time.monotonic()
        threading.Thread(target=self.serve_forever, daemon=True).start()
        try:
            # Short sleeps keep KeyboardInterrupt responsive on all platforms.
            while (idle := self._idle_seconds()) < idle_timeout:
                time.sleep(min(0.5, idle_timeout - idle))
        finally:
            self.shutdown()


def _port_free_on(host: str, port: int) -> bool:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    try:
        sock = socket.socket(family, socket.SOCK_STREAM)
    except OSError:
        return True  # Address family not supported on this host
    with sock:
        _set_bind_options(sock)
        try:
            sock.bind((host, port))
        except OSError as e:
            return e.errno not in _SKIPPABLE_BIND_ERRNOS
    return True


def _port_in_use(port: int) -> bool:
    return not all(_port_free_on(host, port) for host in _CONFLICT_PROBE_HOSTS)


def create_server(
    directory: str | os.PathLike[str],
    bind: str = "127.0.0.1",
    port: int | None = None,
    port_range: tuple[int, int] = (DEFAULT_PORT_RANGE_MIN, DEFAULT_PORT_RANGE_MAX),
) -> QuickHTTPServer:
    """Create a [`QuickHTTPServer`][quickhttp.http_server.QuickHTTPServer] bound to an
    available port.

    A port counts as in use if it's bound on `bind` or on any loopback (`127.0.0.1`, `::1`) or
    all-interfaces (`0.0.0.0`, `::`) address, so that `localhost` can't reach a different server.

    If `port` is None, tries each port in `port_range` in ascending order and uses the first
    one that isn't in use. If no port in the range is available, uses a port chosen by the
    operating system.

    Args:
        directory (str | os.PathLike[str]): Directory to serve.
        bind (str, optional): Address to bind to. A hostname binds the first address it resolves
            to. Defaults to `"127.0.0.1"`.
        port (int | None, optional): Port to bind to. `0` uses a port chosen by the operating
            system. Defaults to None, which searches `port_range`.
        port_range (tuple[int, int], optional): Inclusive range of ports to search. Defaults to
            ([DEFAULT_PORT_RANGE_MIN][quickhttp.http_server.DEFAULT_PORT_RANGE_MIN],
            [DEFAULT_PORT_RANGE_MAX][quickhttp.http_server.DEFAULT_PORT_RANGE_MAX]).

    Raises:
        InvalidPortError: If `port` isn't between 0 and 65535.
        InvalidPortRangeError: If `port` is None and `port_range` isn't a valid range of ports.
        OSError: If `bind` can't be resolved, if `port` is given and is in use or can't be
            bound, or if binding fails for a reason other than the port being in use or not
            permitted.

    Returns:
        QuickHTTPServer: A server bound to the address and port, not yet serving.
    """
    if port is not None and not 0 <= port <= 65535:
        raise InvalidPortError(f"Invalid port {port}. The port must be between 0 and 65535.")
    range_min, range_max = port_range
    if port is None and not 1 <= range_min <= range_max <= 65535:
        raise InvalidPortRangeError(
            f"Invalid port range [{range_min}, {range_max}]. The minimum must be at least 1, "
            "the maximum at most 65535, and the minimum no greater than the maximum."
        )
    host = str(
        socket.getaddrinfo(bind, 0, type=socket.SOCK_STREAM, flags=socket.AI_PASSIVE)[0][4][0]
    )

    if port is not None:
        if port != 0 and _port_in_use(port):
            raise OSError(errno.EADDRINUSE, "Address already in use")
        return QuickHTTPServer((host, port), directory)

    for candidate in range(range_min, range_max + 1):
        if _port_in_use(candidate):
            continue
        try:
            return QuickHTTPServer((host, candidate), directory)
        except OSError as e:
            if e.errno in _SKIPPABLE_BIND_ERRNOS:
                continue
            raise
    return QuickHTTPServer((host, 0), directory)
