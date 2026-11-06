import argparse
from collections.abc import Sequence
from datetime import timedelta
from pathlib import Path
import sys

from pytimeparse import parse

from quickhttp import __version__
from quickhttp.exceptions import InvalidPortError, InvalidPortRangeError
from quickhttp.http_server import DEFAULT_PORT_RANGE_MAX, DEFAULT_PORT_RANGE_MIN, create_server


def _duration(value: str) -> float:
    seconds = parse(value)
    if seconds is None:
        raise argparse.ArgumentTypeError(f"Unable to parse {value!r} as a duration.")
    if seconds <= 0:
        raise argparse.ArgumentTypeError(f"Duration must be positive, got {value!r}.")
    return seconds


def _parser(prog: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description=(
            "Lightweight CLI that wraps Python's `http.server` with automatic port-finding and "
            "shutdown."
        ),
    )
    parser.add_argument(
        "directory", nargs="?", default=".", type=Path, help="Directory to serve. (default: .)"
    )
    parser.add_argument(
        "-t",
        "--timeout",
        default="10m",
        type=_duration,
        metavar="DURATION",
        help=(
            "Time to keep server alive for after most recent request. Accepts time expressions "
            "parsable by pytimeparse, such as '10m' or '10:00'. (default: 10m)"
        ),
    )
    parser.add_argument(
        "-b",
        "--bind",
        default="127.0.0.1",
        metavar="ADDRESS",
        help=(
            "Address to bind server to. '127.0.0.1' (IPv4) or '::1' (IPv6) will only be "
            "accessible from this computer. '0.0.0.0' (IPv4) or '::' (IPv4 and IPv6) is all "
            "interfaces (IP addresses) on this computer, meaning that it can be accessible by "
            "other computers at your IP address. A hostname binds the first address it "
            "resolves to. (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        help=(
            "Port to use. 0 uses a port chosen by the operating system. If specified, ignores "
            "the port range options. If not specified, searches the port range for an available "
            "port, and uses a port chosen by the operating system if none is available."
        ),
    )
    parser.add_argument(
        "--port-range-min",
        default=DEFAULT_PORT_RANGE_MIN,
        type=int,
        metavar="PORT",
        help="Minimum of range to search for an available port. (default: %(default)s)",
    )
    parser.add_argument(
        "--port-range-max",
        default=DEFAULT_PORT_RANGE_MAX,
        type=int,
        metavar="PORT",
        help="Maximum of range to search for an available port. (default: %(default)s)",
    )
    parser.add_argument(
        "--version", action="version", version=__version__, help="Show version and exit."
    )
    return parser


def main(argv: Sequence[str] | None = None, prog: str | None = None) -> None:
    """Run the quickhttp command-line program."""
    parser = _parser(prog)
    args = parser.parse_args(argv)
    directory: Path = args.directory
    timeout_sec: float = args.timeout
    bind: str = args.bind
    port: int | None = args.port
    port_range_min: int = args.port_range_min
    port_range_max: int = args.port_range_max

    if not directory.exists():
        parser.error(f"argument directory: Directory '{directory}' does not exist.")
    if not directory.is_dir():
        parser.error(f"argument directory: '{directory}' is not a directory.")
    try:
        server = create_server(
            directory, bind=bind, port=port, port_range=(port_range_min, port_range_max)
        )
    except InvalidPortError as e:
        parser.error(f"argument -p/--port: {e}")
    except InvalidPortRangeError as e:
        parser.error(f"argument --port-range-min/--port-range-max: {e}")
    except OSError as e:
        if port is None:
            target = bind
        elif ":" in bind:
            target = f"[{bind}]:{port}"
        else:
            target = f"{bind}:{port}"
        print(f"Could not bind to {target}: {e.strerror or e}", file=sys.stderr)
        sys.exit(1)

    with server:
        if port is None and not port_range_min <= server.port <= port_range_max:
            print(
                f"No available port in range [{port_range_min}, {port_range_max}]. "
                f"Using port {server.port} chosen by the operating system."
            )
        print(
            f"Serving {directory.resolve()} at {server.url}. Shutting down after "
            f"{timedelta(seconds=timeout_sec)} without requests.",
            flush=True,
        )
        try:
            server.serve_until_idle(timeout_sec)
            print("Timeout reached.")
        except KeyboardInterrupt:
            print(" KeyboardInterrupt received.")
    print("Server closed.")
