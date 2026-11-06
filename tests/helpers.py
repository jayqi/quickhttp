from contextlib import contextmanager
import socket


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
