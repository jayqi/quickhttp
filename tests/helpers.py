from contextlib import contextmanager
import os
import random
import socket

from quickhttp.http_server import QuickHTTPServer


@contextmanager
def held_port(host: str = "127.0.0.1", port: int = 0, v6only: bool | None = None):
    """Listen on a port with a plain socket, as an unrelated program would. `v6only` sets
    IPV6_V6ONLY on an IPv6 socket instead of leaving the platform default.
    """
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        if v6only is not None:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, v6only)
        sock.bind((host, port))
        sock.listen()
        yield sock.getsockname()[1]


def free_port_pair() -> int:
    """Return a port N such that a server can bind N and N + 1 on 127.0.0.1. N is drawn from
    below the operating systems' default ephemeral port ranges, which start at 32768 on Linux
    and 49152 on macOS and Windows, so the OS doesn't assign N + 1 to another socket while the
    test runs.
    """
    for _ in range(50):
        port = random.randrange(20000, 30000)
        try:
            with (
                QuickHTTPServer(("127.0.0.1", port), os.curdir),
                QuickHTTPServer(("127.0.0.1", port + 1), os.curdir),
            ):
                return port
        except OSError:
            continue
    raise RuntimeError("Unable to find two consecutive free ports.")
