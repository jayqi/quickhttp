# Release Notes

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
