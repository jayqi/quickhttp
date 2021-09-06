from datetime import timedelta
from pathlib import Path
from typing import Optional

from pytimeparse import parse
import typer

from quickhttp._version import __version__
from quickhttp.http_server import (
    DEFAULT_PORT_RANGE_MIN,
    DEFAULT_PORT_RANGE_MAX,
    DEFAULT_PORT_MAX_TRIES,
    DEFAULT_PORT_SEARCH_TYPE,
    find_available_port,
    run_timed_http_server,
    SearchType,
)

app = typer.Typer()


def version_callback(value: bool):
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.command()
def quickhttp(
    directory: Path = typer.Argument(
        ".", dir_okay=True, file_okay=False, readable=True, help="Directory to serve."
    ),
    timeout: str = typer.Option(
        "10m",
        "--timeout",
        "-t",
        help=(
            "Time to keep server alive for after most recent request. Accepts time expressions "
            "parsable by pytime parse, such as '10m' or '10:00'."
        ),
    ),
    bind: str = typer.Option(
        "127.0.0.1",
        "--bind",
        "-b",
        help=(
            "Address to bind server to. '127.0.0.1' (or 'localhost') will only be accessible from "
            "this computer. '0.0.0.0' is all interfaces (IP addresses) on this computer, meaning "
            "that it can be accessible by other computers at your IP address."
        ),
    ),
    port: Optional[int] = typer.Option(
        None,
        "--port",
        "-p",
        help=(
            "Port to use. If None (default), will automatically search for an open port using "
            "the other port-related options. If specified, ignores other port-related options."
        ),
    ),
    port_range_min: int = typer.Option(
        DEFAULT_PORT_RANGE_MIN, help="Minimum of range to search for an open port."
    ),
    port_range_max: int = typer.Option(
        DEFAULT_PORT_RANGE_MAX, help="Maximum of range to search for an open port."
    ),
    port_max_tries: int = typer.Option(
        DEFAULT_PORT_MAX_TRIES, help="Maximum number of ports to check."
    ),
    port_search_type: SearchType = typer.Option(
        DEFAULT_PORT_SEARCH_TYPE, help="Type of search to use."
    ),
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
        show_default=False,
    ),
):
    """Lightweight CLI that wraps Python's `http.server` with automatic port-finding and shutdown."""
    timeout_sec = parse(timeout)
    if not port:
        port = find_available_port(
            range_min=port_range_min,
            range_max=port_range_max,
            max_tries=port_max_tries,
            search_type=port_search_type,
        )
    typer.echo(
        f"Starting http.server at http://{bind}:{port} for directory [{directory}]. "
        f"Server will stay alive for {str(timedelta(seconds=timeout_sec))}."
    )
    run_timed_http_server(address=bind, port=port, directory=directory, timeout=timeout_sec)
    typer.echo("Server closed.")
