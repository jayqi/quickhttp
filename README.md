# quickhttp

[![PyPI](https://img.shields.io/pypi/v/quickhttp.svg)](https://pypi.org/project/quickhttp/)
[![tests](https://github.com/jayqi/quickhttp/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/jayqi/quickhttp/actions/workflows/tests.yml?query=workflow%3Atests+branch%3Amain)
[![coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/jayqi/quickhttp/badges/coverage.json)](https://github.com/jayqi/quickhttp/actions/workflows/tests.yml?query=branch%3Amain)

`quickhttp` is a lightweight CLI that wraps Python's `http.server` with automatic port-finding and automatic shutdown after a configurable idle duration.

## Features

- Automatically finds and uses an available port, preferring the 8000–8999 range.
- Has a keep-alive time after which it will shut down automatically if no requests are received, in case you forget about it.
- More secure default of `127.0.0.1` (`localhost`) instead of `0.0.0.0`.
- Supports IPv6, including `::` to serve on all interfaces over both IPv4 and IPv6.
- Easier to type and autocomplete than `python -m http.server`.

## Installation

If you're using [uv](https://docs.astral.sh/uv/), you can immediately run it without installing by using `uvx`:

```bash
uvx quickhttp
```

To install it to be available for later use, you can use any method that installs from [PyPI](https://pypi.org/project/quickhttp/). I recommend using [`uv tool`](https://docs.astral.sh/uv/guides/tools/) or [`pipx`](https://pipxproject.github.io/pipx/) to manage Python command-line programs.

```bash
uvx quickhttp
# or
uv tool install quickhttp
# or
pipx install quickhttp
# or
pip install quickhttp
```


### Development Version

To run the development version of this program, get it directly from GitHub.

```bash
uvx "quickhttp @ git+https://github.com/jayqi/quickhttp.git"
```

## Documentation

```bash
quickhttp --help
```

```text
Usage: quickhttp [OPTIONS] [directory]

Lightweight CLI that wraps Python's `http.server` with automatic port-finding
and shutdown.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   directory      <directory>  Directory to serve. [default: .]               │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --timeout             -t      <str>  Time to keep server alive for after     │
│                                      most recent request. Accepts time       │
│                                      expressions parsable by pytimeparse,    │
│                                      such as '10m' or '10:00'.               │
│                                      [default: 10m]                          │
│ --bind                -b      <str>  Address to bind server to. '127.0.0.1'  │
│                                      (or 'localhost') will only be           │
│                                      accessible from this computer.          │
│                                      '0.0.0.0' (IPv4) or '::' (IPv4 and      │
│                                      IPv6) is all interfaces (IP addresses)  │
│                                      on this computer, meaning that it can   │
│                                      be accessible by other computers at     │
│                                      your IP address.                        │
│                                      [default: 127.0.0.1]                    │
│ --port                -p      <int>  Port to use. 0 uses a port chosen by    │
│                                      the operating system. If not specified, │
│                                      searches the port range for an          │
│                                      available port, and uses a port chosen  │
│                                      by the operating system if none is      │
│                                      available.                              │
│ --port-range-min              <int>  Minimum of range to search for an       │
│                                      available port.                         │
│                                      [default: 8000]                         │
│ --port-range-max              <int>  Maximum of range to search for an       │
│                                      available port.                         │
│                                      [default: 8999]                         │
│ --version                            Show version and exit.                  │
│ --install-completion                 Install completion for the current      │
│                                      shell.                                  │
│ --show-completion                    Show completion for the current shell,  │
│                                      to copy it or customize the             │
│                                      installation.                           │
│ --help                               Show this message and exit.             │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Why use `quickhttp`?

- `python -m http.server` is a pain to type. `quickhttp` is shorter and can autocomplete. (But you can still do `python -m quickhttp` too if you really want to.)
- If you try starting `python -m http.server` and port 8000 is unavailable, you get `OSError: [Errno 48] Address already in use`. Then you have to choose another port and try again. `quickhttp` deals with ports automatically for you.
- `quickhttp` will automatically shutdown after the keep-alive time expires. This defaults to 10 minutes. I often start up an HTTP server to look at something, then open a new tab to continue doing things, and then I forget about the server.
- `python -m http.server` defaults to 0.0.0.0, which may make your server accessible to other people at your computer's IP address. This can be a security vulnerability, but isn't necessarily obvious to people who just want to quickly serve some static files.
