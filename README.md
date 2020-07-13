# quickhttp

`quickhttp` is a lightweight CLI that wraps Python's `http.server` with automatic port-finding and automatic shutdown after a certain duration.

## Features

- Automatically finds and uses an available port.
- Has a keep-alive time and shuts down automatically, in case you forget about it.
- Easier to type and autocomplete than `python -m http.server`.

## Installation

Requires Python 3.6 or higher.

### Development Version

To install the development version of this program, get it directly from GitHub:

```bash
pip install -e git+https://github.com/jayqi/quickhttp.git
```

## Documentation

```bash
quickhttp --help
```

```
Usage: quickhttp [OPTIONS] [DIRECTORY]

Arguments:
  [DIRECTORY]  Directory to serve.  [default: .]

Options:
  -t, --time TEXT                 Time to keep server alive for. Accepts time
                                  expressions parsable by pytimeparse, such as
                                  '10m' or '10:00'.  [default: 10m]

  -p, --port INTEGER              Port to use. If None (default), will
                                  automatically find an open port using other
                                  options. If specified, ignores other
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

  --help                          Show this message and exit.```
```

## Why use `quickhttp`?

- `python -m http.server` is a pain to type. `quickhttp` is shorter and can autocomplete. (But you can still do `pythom -m quickhttp` too if you really want to.)
- If you try starting `python -m http.server` and port 8000 is unavailable, you get `OSError: [Errno 48] Address already in use`. Then you have to choose another port and try again. `quickhttp` deals with ports automatically for you.
- `quickhttp` will automatically shutdown after the keep-alive time expires. This defaults to 10 minutes. I often will start up an HTTP server to look at something, and then I open a new tab to continue doing things, and then I forget about the server.
