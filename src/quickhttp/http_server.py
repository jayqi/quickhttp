from collections.abc import Generator
from contextlib import closing, contextmanager, suppress
from enum import Enum
import errno
from functools import partial
from http.server import (
    BaseHTTPRequestHandler,
    HTTPServer,
    SimpleHTTPRequestHandler,
    ThreadingHTTPServer,
)
from itertools import islice
import os
import random
import socket
import threading
import time
from typing import Callable, Iterable, Tuple, Union, cast

import typer

from quickhttp.exceptions import (
    InvalidPortRangeError,
    InvalidSearchTypeError,
    NoAvailablePortFoundError,
)


def is_port_available(port: int) -> bool:
    """Check if port is available (not in use) on the local host. This is determined by attempting
    to create a socket connection with that port. If the connection is successful, that means
    something is using the port.

    Args:
        port (int): port to check.

    Returns:
        bool: If that port is available (not in use).
    """
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            # Successful connection
            return False
    return True


class SearchType(str, Enum):
    """Enum. Available types of search for
    [`find_available_port`][quickhttp.http_server.find_available_port].

    Attributes:
        sequential: Search ports sequentially in ascending order, starting with range_min.
        random: Search ports randomly within the interval [range_min, range_max].
    """

    sequential = "sequential"
    random = "random"


DEFAULT_PORT_RANGE_MIN: int = 8000
"""Default minimum of open port search range."""
DEFAULT_PORT_RANGE_MAX: int = 8999
"""Default maximum of open port search range."""
DEFAULT_PORT_MAX_TRIES: int = 50
"""Default maximum number of search attempts for an open port."""
DEFAULT_PORT_SEARCH_TYPE: SearchType = SearchType.sequential
"""Default type of search for [`find_available_port`][quickhttp.http_server.find_available_port].
See [`SearchType`][quickhttp.http_server.SearchType].
"""


def find_available_port(
    range_min: int = DEFAULT_PORT_RANGE_MIN,
    range_max: int = DEFAULT_PORT_RANGE_MAX,
    max_tries: int = DEFAULT_PORT_MAX_TRIES,
    search_type: SearchType = DEFAULT_PORT_SEARCH_TYPE,
) -> int:
    """Searches for an available port (not in use) on the local host.

    Args:
        range_min (int, optional): Minimum of range to search. Defaults to
            [DEFAULT_PORT_RANGE_MIN][quickhttp.http_server.DEFAULT_PORT_RANGE_MIN].
        range_max (int, optional): Maximum of range to search. Defaults to
            [DEFAULT_PORT_RANGE_MAX][quickhttp.http_server.DEFAULT_PORT_RANGE_MAX].
        max_tries (int, optional): Maximum number of ports to check. Defaults to
            [DEFAULT_PORT_MAX_TRIES][quickhttp.http_server.DEFAULT_PORT_MAX_TRIES].
        search_type (SearchType, optional): Type of search. See
            [SearchType][quickhttp.http_server.SearchType] enum for valid values. Defaults to
            [DEFAULT_PORT_SEARCH_TYPE][quickhttp.http_server.DEFAULT_PORT_SEARCH_TYPE].

    Raises:
        InvalidSearchTypeError: If search_type is invalid.
        NoAvailablePortFoundError: If no available ports found within max_tries.

    Returns:
        int: An available port.
    """
    max_tries = min(max_tries, range_max - range_min + 1)

    to_try: Iterable[int]
    if search_type == SearchType.sequential:
        to_try = islice(range(range_min, range_max + 1), max_tries)
    elif search_type == SearchType.random:
        to_try = random.sample(range(range_min, range_max + 1), max_tries)
    else:
        msg = (
            f"Invalid search_type {search_type}. Available options are "
            f"[{'|'.join(level.value for level in SearchType)}]."
        )
        raise InvalidSearchTypeError(msg)

    for port in to_try:
        if is_port_available(port=port):
            return port

    raise NoAvailablePortFoundError(
        f"Unable to find available port in range [{range_min}, {range_max}] with "
        f"{SearchType(search_type).value} search in {max_tries} tries."
    )


class TimedHTTPServer(HTTPServer):
    """Subclass of [`http.server.HTTPServer`](https://docs.python.org/3/library/http.server.html)
    that tracks timeout status.
    """

    def __init__(
        self,
        server_address: Tuple[str, int],
        RequestHandlerClass: Callable[..., BaseHTTPRequestHandler],
        timeout: float,
    ):
        self.timeout = timeout
        self.timeout_reached = False
        super().__init__(server_address=server_address, RequestHandlerClass=RequestHandlerClass)

    def handle_timeout(self):
        """Called if no new request arrives within self.timeout."""
        self.timeout_reached = True


def run_timed_http_server(
    address: str, port: int, directory: Union[str, os.PathLike], timeout: float
):
    """Start a [`TimedHTTPServer`][quickhttp.http_server.TimedHTTPServer] with specified timeout.

    Args:
        address (str): Address to bind the server to.
        port (int): Port to use.
        directory (Union[str, os.PathLike]): Directory to serve.
        timeout (float): Time to keep server alive for, in seconds.
    """
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))

    with TimedHTTPServer(
        server_address=(address, port), RequestHandlerClass=handler, timeout=timeout
    ) as httpd:
        try:
            while not httpd.timeout_reached:
                httpd.handle_request()
            typer.echo("Timeout reached.")
        except KeyboardInterrupt:
            typer.echo(" KeyboardInterrupt received.")


_SKIPPABLE_BIND_ERRNOS = frozenset(
    code
    for name in ("EADDRINUSE", "EACCES", "WSAEADDRINUSE", "WSAEACCES")
    if (code := getattr(errno, name, None)) is not None
)
"""Bind errors that mean a port is in use or not permitted, as opposed to a bad address."""

_LOOPBACK_SIBLINGS = {"127.0.0.1": "::1", "::1": "127.0.0.1"}


def _set_bind_options(sock: socket.socket) -> None:
    # On Windows, SO_REUSEADDR allows binding a port that another socket is listening on.
    if os.name == "nt":
        sock.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE"), 1)
    else:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


class _Handler(SimpleHTTPRequestHandler):
    timeout = 60

    def do_GET(self):
        with self._server().track_request():
            super().do_GET()

    def do_HEAD(self):
        with self._server().track_request():
            super().do_HEAD()

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
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
        super().server_bind()

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
    def track_request(self) -> Generator[None, None, None]:
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


def create_server(
    directory: str | os.PathLike[str],
    bind: str = "127.0.0.1",
    port: int | None = None,
    port_range: tuple[int, int] = (DEFAULT_PORT_RANGE_MIN, DEFAULT_PORT_RANGE_MAX),
) -> QuickHTTPServer:
    """Create a [`QuickHTTPServer`][quickhttp.http_server.QuickHTTPServer] bound to an
    available port.

    If `port` is None, tries each port in `port_range` in ascending order and uses the first
    one that can be bound. When binding `127.0.0.1` or `::1`, a port is also skipped if it is
    in use on the other one, so that `localhost` can't reach a different server. If no port
    in the range is available, uses a port chosen by the operating system.

    Args:
        directory (str | os.PathLike[str]): Directory to serve.
        bind (str, optional): Address to bind to. Defaults to `"127.0.0.1"`.
        port (int | None, optional): Port to bind to. `0` uses a port chosen by the operating
            system. Defaults to None, which searches `port_range`.
        port_range (tuple[int, int], optional): Inclusive range of ports to search. Defaults to
            ([DEFAULT_PORT_RANGE_MIN][quickhttp.http_server.DEFAULT_PORT_RANGE_MIN],
            [DEFAULT_PORT_RANGE_MAX][quickhttp.http_server.DEFAULT_PORT_RANGE_MAX]).

    Raises:
        InvalidPortRangeError: If `port` is None and `port_range` isn't a valid range of ports.
        OSError: If binding fails for a reason other than the port being in use or not
            permitted, such as an address that can't be resolved, or if `port` is given and
            can't be bound.

    Returns:
        QuickHTTPServer: A server bound to the address and port, not yet serving.
    """
    if port is not None:
        return QuickHTTPServer((bind, port), directory)

    range_min, range_max = port_range
    if not 1 <= range_min <= range_max <= 65535:
        raise InvalidPortRangeError(
            f"Invalid port range [{range_min}, {range_max}]. The minimum must be at least 1, "
            "the maximum at most 65535, and the minimum no greater than the maximum."
        )
    for candidate in range(range_min, range_max + 1):
        try:
            server = QuickHTTPServer((bind, candidate), directory)
        except socket.gaierror:
            raise
        except OSError as e:
            if e.errno in _SKIPPABLE_BIND_ERRNOS:
                continue
            raise
        sibling = _LOOPBACK_SIBLINGS.get(server.host)
        if sibling is not None and not _port_free_on(sibling, candidate):
            server.server_close()
            continue
        return server
    return QuickHTTPServer((bind, 0), directory)
