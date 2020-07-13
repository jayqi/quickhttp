from contextlib import closing, contextmanager
from enum import Enum
from itertools import islice
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
from pathlib import Path
import random
import socket
from threading import Thread
from time import sleep

try:
    import importlib.metadata as importlib_metadata
except ModuleNotFoundError:
    import importlib_metadata


__version__ = importlib_metadata.version(__name__.split(".", 1)[0])


DEFAULT_PORT_RANGE_MIN = 8000
DEFAULT_PORT_RANGE_MAX = 8999
DEFAULT_PORT_MAX_TRIES = 50
DEFAULT_PORT_SEARCH_TYPE = "sequential"


def is_port_available(port: int, host: str = "0.0.0.0") -> bool:
    """Check if port is available (not in use) on host.

    Args:
        port (int): port to check.
        host (str, optional): Host to check port on. Defaults to "0.0.0.0".

    Returns:
        bool: If that port is available.
    """
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        if sock.connect_ex((host, port)) == 0:
            return False
    return True


class SearchType(str, Enum):
    """Available types of search for [find_available_port][quickhttp.core.find_available_port]

    Attributes:
        sequential: Search ports sequentially, starting with range_min.
        random: Search ports randomly within [range_min, range_max].
    """

    sequential = "sequential"
    random = "random"


class NoAvailablePortFound(Exception):
    pass


def find_available_port(
    range_min: int = DEFAULT_PORT_RANGE_MIN,
    range_max: int = DEFAULT_PORT_RANGE_MAX,
    max_tries: int = DEFAULT_PORT_MAX_TRIES,
    search_type: SearchType = DEFAULT_PORT_SEARCH_TYPE,
    host: str = "0.0.0.0",
) -> int:

    if search_type == SearchType.sequential:
        to_try = islice(range(range_min, range_max + 1), max_tries)
    elif search_type == SearchType.random:
        to_try = random.sample(range(range_min, range_max + 1), max_tries)
    else:
        msg = (
            f"Invalid search_type {search_type}. Available options are "
            f"[{'|'.join(level.value for level in SearchType)}]."
        )
        raise ValueError(msg)

    for port in to_try:
        if is_port_available(port=port, host=host):
            return port

    params = {
        "range_min": range_min,
        "range_max": range_max,
        "search_type": SearchType(search_type).value,
    }
    msg = f"Unable to find available port in {max_tries} tries given parameters: {params}"
    raise NoAvailablePortFound(msg)


find_available_port.__doc__ = f"""Find an available port (not in use) given parameters.

Args:
    range_min (int, optional): Minimum of range to search. Defaults to
        {DEFAULT_PORT_RANGE_MIN}.
    range_max (int, optional): Maximum of range to search. Defaults to
        {DEFAULT_PORT_RANGE_MAX}.
    max_tries (int, optional): Maximum number of ports to check. Defaults to
        {DEFAULT_PORT_MAX_TRIES}.
    search_type (SearchType, optional): Type of search. One of
        [{'|'.join(level.value for level in SearchType)}]. Defaults to
        {DEFAULT_PORT_SEARCH_TYPE}.
    host (str, optional): Host to find ports on. Defaults to "0.0.0.0".

Raises:
    ValueError: If search_type is invalid.
    NoAvailablePortFound: If no available ports found within max_tries.

Returns:
    int: An available port
"""


@contextmanager
def working_directory(directory: Path):
    """Context manager that changes working directory and returns to previous on exit.

    Args:
        directory (Path): Directory to temporarily change to.
    """
    prev_cwd = Path.cwd()
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def run_timed_http_server(port: int, directory: Path, time: int):
    """Start a [HTTPServer](https://docs.python.org/3/library/http.server.html) for specified time.

    Args:
        port (int): Port to use.
        directory (Path): Directory to serve.
        time (int): Time to keep server alive for, in seconds.
    """
    httpd = HTTPServer(server_address=("", port), RequestHandlerClass=SimpleHTTPRequestHandler)
    with working_directory(directory):
        thread = Thread(target=httpd.serve_forever)
        thread.daemon = True
        thread.start()
        try:
            sleep(time)
        except KeyboardInterrupt:
            pass
        httpd.shutdown()
