# Release Notes

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
