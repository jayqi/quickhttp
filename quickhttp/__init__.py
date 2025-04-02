import importlib.metadata

from quickhttp.http_server import (
    TimedHTTPServer,
    run_timed_http_server,
)

__version__ = importlib.metadata.version("quickhttp")


__all__ = [
    "run_timed_http_server",
    "TimedHTTPServer",
]

__version__
