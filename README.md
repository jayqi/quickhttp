# quickhttp

[![Docs Status](https://img.shields.io/badge/docs-stable-informational)](https://jayqi.github.io/quickhttp/)
[![PyPI](https://img.shields.io/pypi/v/quickhttp.svg)](https://pypi.org/project/quickhttp/)
[![tests](https://github.com/jayqi/quickhttp/workflows/tests/badge.svg?branch=main)](https://github.com/jayqi/quickhttp/actions?query=workflow%3Atests+branch%3Amain)
[![codecov](https://codecov.io/gh/jayqi/quickhttp/branch/main/graph/badge.svg)](https://codecov.io/gh/jayqi/quickhttp)

`quickhttp` is a lightweight CLI that wraps Python's `http.server` with automatic port-finding and automatic shutdown after a configurable idle duration.

## Features

- Automatically finds and uses an available port.
- Has a keep-alive time after which it will shut down automatically if no requests are received, in case you forget about it.
- More secure default of `127.0.0.1` (`localhost`) instead of `0.0.0.0`.
- Easier to type and autocomplete than `python -m http.server`.

## Installation

You can get `quickhttp` from [PyPI](https://pypi.org/project/quickhttp/). I recommend using [`pipx`](https://pipxproject.github.io/pipx/) to manage Python command-line programs:

```bash
pipx install quickhttp
```

You can also install normally using regular `pip`:

```bash
pip install quickhttp
```

Requires Python 3.7 or higher. For Python 3.6, install [v1.0.0](https://pypi.org/project/quickhttp/1.0.0/).

### Development Version

To install the development version of this program, get it directly from GitHub.

```bash
pipx install git+https://github.com/jayqi/quickhttp.git
```

## Documentation

```bash
quickhttp --help
```

```text
Usage: quickhttp [OPTIONS] [DIRECTORY]

  Lightweight CLI that wraps Python's `http.server` with automatic port-
  finding and shutdown.

Arguments:
  [DIRECTORY]  Directory to serve.  [default: .]

Options:
  -t, --timeout TEXT              Time to keep server alive for after most
                                  recent request. Accepts time expressions
                                  parsable by pytimeparse, such as '10m' or
                                  '10:00'.  [default: 10m]

  -b, --bind TEXT                 Address to bind server to. '127.0.0.1' (or
                                  'localhost') will only be accessible from
                                  this computer. '0.0.0.0' is all interfaces
                                  (IP addresses) on this computer, meaning
                                  that it can be accessible by other computers
                                  at your IP address.  [default: 127.0.0.1]

  -p, --port INTEGER              Port to use. If None (default), will
                                  automatically search for an open port using
                                  the other port-related options. If
                                  specified, ignores other port-related
                                  options.

  --port-range-min INTEGER        Minimum of range to search for an open port.
                                  [default: 8000]

  --port-range-max INTEGER        Maximum of range to search for an open port.
                                  [default: 8999]

  --port-max-tries INTEGER        Maximum number of ports to check.  [default:
                                  50]

  --port-search-type [sequential|random]
                                  Type of search to use.  [default:
                                  sequential]

  --version                       Show version and exit.
  --install-completion [bash|zsh|fish|powershell|pwsh]
                                  Install completion for the specified shell.
  --show-completion [bash|zsh|fish|powershell|pwsh]
                                  Show completion for the specified shell, to
                                  copy it or customize the installation.

  --help                          Show this message and exit.
```

## Why use `quickhttp`?

- `python -m http.server` is a pain to type. `quickhttp` is shorter and can autocomplete. (But you can still do `python -m quickhttp` too if you really want to.)
- If you try starting `python -m http.server` and port 8000 is unavailable, you get `OSError: [Errno 48] Address already in use`. Then you have to choose another port and try again. `quickhttp` deals with ports automatically for you.
- `quickhttp` will automatically shutdown after the keep-alive time expires. This defaults to 10 minutes. I often start up an HTTP server to look at something, then open a new tab to continue doing things, and then I forget about the server.
- `python -m http.server` defaults to 0.0.0.0, which may make your server accessible to other people at your computer's IP address. This is a security vulnerability, but isn't necessarily obvious to people who just want to quickly serve some static files.
