# Release Notes

## v3.0.0 - Unreleased

- Changed the server to handle requests concurrently. Previously, a connection that sent nothing, such as one a browser opens ahead of time, blocked all other requests and kept the server from shutting down, which could show as a blank page.
- Changed the port search to bind each candidate port instead of connecting to it. It now detects ports in use on any address, and skips ports in use on the other loopback address (`::1` when binding `127.0.0.1`, and the reverse) so that `localhost` can't reach a different server.
- Changed the port search to use a port chosen by the operating system when no port in the range is available, instead of failing.
- Changed `--port 0` to use a port chosen by the operating system. It previously searched the port range.
- Changed the idle timeout to wait for in-progress requests to finish, and to count from the end of the most recent request.
- Added support for IPv6 bind addresses, including `::` for all interfaces over both IPv4 and IPv6.
- Added a `Cache-Control: no-cache` header to responses, so that browsers don't show stale files.
- Added validation that the served directory exists, that `--timeout` is positive, and that the port range is valid.
- Fixed slow startup on machines where looking up the computer's own hostname is slow. The server no longer does that lookup.
- Changed bind failures, such as a port in use or an address that can't be resolved, to be reported as an error message instead of a traceback.
- Removed the `--port-search-type` and `--port-max-tries` options. The port search now always tries ports in ascending order.
- Removed `TimedHTTPServer`, `run_timed_http_server`, `is_port_available`, `find_available_port`, `SearchType`, `NoAvailablePortFoundError`, and `InvalidSearchTypeError` from the Python API.
- Added `QuickHTTPServer`, `create_server`, and `InvalidPortRangeError` to the Python API.

## v2.2.0 - 2026-11-05

- Removed support for Python 3.8, 3.9, and 3.10
- Added support for Python 3.14 and 3.15
- Fixed an unhandled `TypeError` when the `--timeout` value can't be parsed. It's now reported as a usage error.
- Changed the source distribution to contain only the package source, `pyproject.toml`, README, and LICENSE. It previously also included tests and other repository files. This is a result of changing the build backend from hatchling to uv_build.

## v2.1.0 - 2025-04-02

- Removed support for Python 3.7
- Added support for Python 3.12 and 3.13
- Changed package metadata to PEP 621 from Poetry.

## v2.0.0 - 2023-02-11

- Removed support for Python 3.6.
- Removed `DirectoryHTTPRequestHandler` which was only needed for Python 3.6.

## v1.0.0 - 2021-09-06

- Changed module organization of package code to be more clear and explicit:
  - Changed name of `quickhttp.core` to `quickhttp.http_server`.
  - Changed name of `quickhttp.quickhttp` to `quickhttp.cli`.
  - Added new `quickhttp.exceptions` module for all package custom exceptions:
    - Added new base exception class `QuickhttpException` that all other exceptions from this package subclass.
    - Added new exception class `InvalidSearchTypeError`.
    - Changed name of `NoAvailablePortFound` to `NoAvailablePortFoundError`. It is now a subclass of `QuickhttpException`.


## v0.2.0 - 2020-11-21

- Changed `--time` option name to `--timeout`.
- Changed timeout time to be from last request instead of from server startup.

## v0.1.0 - 2020-07-16

- Initial release. :sparkles:
