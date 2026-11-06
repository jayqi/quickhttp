from datetime import timedelta
from pathlib import Path
from typing import Optional

from pytimeparse import parse
import typer

from quickhttp import __version__
from quickhttp.exceptions import InvalidPortError, InvalidPortRangeError
from quickhttp.http_server import DEFAULT_PORT_RANGE_MAX, DEFAULT_PORT_RANGE_MIN, create_server

app = typer.Typer()


def version_callback(value: bool):
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.command()
def quickhttp(
    directory: Path = typer.Argument(
        ".",
        exists=True,
        dir_okay=True,
        file_okay=False,
        readable=True,
        help="Directory to serve.",
    ),
    timeout: str = typer.Option(
        "10m",
        "--timeout",
        "-t",
        help=(
            "Time to keep server alive for after most recent request. Accepts time expressions "
            "parsable by pytimeparse, such as '10m' or '10:00'."
        ),
    ),
    bind: str = typer.Option(
        "127.0.0.1",
        "--bind",
        "-b",
        help=(
            "Address to bind server to. '127.0.0.1' (IPv4) or '::1' (IPv6) will only be "
            "accessible from this computer. '0.0.0.0' (IPv4) or '::' (IPv4 and IPv6) is all "
            "interfaces (IP addresses) on this computer, meaning that it can be accessible by "
            "other computers at your IP address. A hostname binds the first address it "
            "resolves to."
        ),
    ),
    port: Optional[int] = typer.Option(
        None,
        "--port",
        "-p",
        help=(
            "Port to use. 0 uses a port chosen by the operating system. If specified, ignores "
            "the port range options. If not specified, searches the port range for an available "
            "port, and uses a port chosen by the operating system if none is available."
        ),
    ),
    port_range_min: int = typer.Option(
        DEFAULT_PORT_RANGE_MIN, help="Minimum of range to search for an available port."
    ),
    port_range_max: int = typer.Option(
        DEFAULT_PORT_RANGE_MAX, help="Maximum of range to search for an available port."
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
    "Lightweight CLI that wraps Python's `http.server` with automatic port-finding and shutdown."
    timeout_sec = parse(timeout)
    if timeout_sec is None:
        raise typer.BadParameter(
            f"Unable to parse {timeout!r} as a duration.", param_hint="'--timeout'"
        )
    if timeout_sec <= 0:
        raise typer.BadParameter(
            f"Duration must be positive, got {timeout!r}.", param_hint="'--timeout'"
        )
    port_range = (port_range_min, port_range_max)
    try:
        server = create_server(directory, bind=bind, port=port, port_range=port_range)
    except InvalidPortError as e:
        raise typer.BadParameter(str(e), param_hint="'--port' / '-p'")
    except InvalidPortRangeError as e:
        raise typer.BadParameter(str(e), param_hint="'--port-range-min' / '--port-range-max'")
    except OSError as e:
        if port is None:
            target = bind
        elif ":" in bind:
            target = f"[{bind}]:{port}"
        else:
            target = f"{bind}:{port}"
        typer.echo(f"Could not bind to {target}: {e.strerror or e}", err=True)
        raise typer.Exit(code=1)

    with server:
        if port is None and not port_range_min <= server.port <= port_range_max:
            typer.echo(
                f"No available port in range [{port_range_min}, {port_range_max}]. "
                f"Using port {server.port} chosen by the operating system."
            )
        typer.echo(
            f"Serving {directory.resolve()} at {server.url}. Shutting down after "
            f"{timedelta(seconds=timeout_sec)} without requests."
        )
        try:
            server.serve_until_idle(timeout_sec)
            typer.echo("Timeout reached.")
        except KeyboardInterrupt:
            typer.echo(" KeyboardInterrupt received.")
    typer.echo("Server closed.")
