import importlib.metadata

from quickhttp.http_server import QuickHTTPServer, create_server

__version__ = importlib.metadata.version("quickhttp")


__all__ = [
    "create_server",
    "QuickHTTPServer",
]
