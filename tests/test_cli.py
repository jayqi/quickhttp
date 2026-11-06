from dataclasses import dataclass
import re
import shutil
import signal
import socket
import subprocess
import sys

import pytest
import requests

from helpers import free_port_pair, held_port
from quickhttp import __version__
from quickhttp.cli import main

URL_PATTERN = re.compile(r" at (http://\S+/)\. ")


@dataclass
class Result:
    exit_code: int
    output: str


def invoke(capsys: pytest.CaptureFixture[str], args: list[str]) -> Result:
    """Run the CLI in this process and capture its exit code and combined stdout and stderr."""
    try:
        main(args)
        exit_code = 0
    except SystemExit as e:
        exit_code = e.code if isinstance(e.code, int) else 1
    captured = capsys.readouterr()
    return Result(exit_code=exit_code, output=captured.out + captured.err)


def start_quickhttp(*args: str) -> tuple[subprocess.Popen[str], str]:
    """Start `python -m quickhttp` and wait until it reports the URL it's serving."""
    process = subprocess.Popen(
        [sys.executable, "-m", "quickhttp", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None
    line = process.stdout.readline()
    match = URL_PATTERN.search(line)
    if match is None:
        process.kill()
        stdout, stderr = process.communicate()
        pytest.fail(f"quickhttp didn't report a URL.\nstdout:\n{line}{stdout}\nstderr:\n{stderr}")
    return process, match.group(1)


def test_help(capsys):
    """Test the CLI with --help flag."""
    result = invoke(capsys, ["--help"])
    assert result.exit_code == 0
    assert "Lightweight CLI that wraps Python's `http.server`" in result.output


def test_version(capsys):
    """Test the CLI with --version flag."""
    result = invoke(capsys, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == __version__


def test_python_m_version():
    """Test the CLI with --version flag."""
    result = subprocess.run(
        [sys.executable, "-m", "quickhttp", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == __version__


def test_invalid_timeout(capsys):
    """Test the CLI with a --timeout value that can't be parsed."""
    result = invoke(capsys, ["--timeout", "garbage"])
    assert result.exit_code == 2
    assert "Unable to parse 'garbage' as a duration." in result.output


@pytest.mark.parametrize("timeout", ["0s", "-5s"])
def test_nonpositive_timeout(timeout, capsys):
    result = invoke(capsys, [f"--timeout={timeout}"])
    assert result.exit_code == 2
    assert f"Duration must be positive, got '{timeout}'." in result.output


def test_nonexistent_directory(tmp_path, capsys):
    result = invoke(capsys, [str(tmp_path / "nonexistent")])
    assert result.exit_code == 2
    assert "does not exist" in result.output


def test_invalid_port_range(capsys):
    result = invoke(capsys, ["--port-range-min", "9000", "--port-range-max", "8000"])
    assert result.exit_code == 2
    assert "Invalid port range [9000, 8000]." in result.output


def test_invalid_port(capsys):
    result = invoke(capsys, ["--port", "65536"])
    assert result.exit_code == 2
    assert "Invalid port 65536." in result.output


@pytest.mark.parametrize(
    "host, target",
    [
        ("127.0.0.1", "127.0.0.1:{port}"),
        pytest.param(
            "::1",
            "[::1]:{port}",
            marks=pytest.mark.skipif(not socket.has_ipv6, reason="IPv6 not available"),
        ),
    ],
)
def test_port_in_use(tmp_path, host, target, capsys):
    with held_port(host) as port:
        result = invoke(capsys, [str(tmp_path), "--bind", host, "--port", str(port)])
    assert result.exit_code == 1
    assert f"Could not bind to {target.format(port=port)}: " in result.output


def test_unresolvable_bind_address(tmp_path, capsys):
    result = invoke(capsys, [str(tmp_path), "--bind", "nonexistent.invalid"])
    assert result.exit_code == 1
    assert "Could not bind to nonexistent.invalid: " in result.output


def test_port_range_search(tmp_path, capsys):
    port = free_port_pair()
    with held_port(port=port):
        result = invoke(
            capsys,
            [
                str(tmp_path),
                "--timeout",
                "0.1s",
                "--port-range-min",
                str(port),
                "--port-range-max",
                str(port + 1),
            ],
        )
    assert result.exit_code == 0
    assert f"at http://127.0.0.1:{port + 1}/." in result.output


def test_port_range_taken_falls_back_to_os_port(tmp_path, capsys):
    port = free_port_pair()
    with held_port(port=port), held_port(port=port + 1):
        result = invoke(
            capsys,
            [
                str(tmp_path),
                "--timeout",
                "0.1s",
                "--port-range-min",
                str(port),
                "--port-range-max",
                str(port + 1),
            ],
        )
    assert result.exit_code == 0
    assert f"No available port in range [{port}, {port + 1}]." in result.output
    assert "Server closed." in result.output


def test_serves_until_timeout(html_file, tmp_path):
    shutil.copy(html_file, tmp_path)
    process, url = start_quickhttp(str(tmp_path), "--port", "0", "--timeout", "2s")

    response = requests.get(url, timeout=5)
    assert response.status_code == 200
    assert response.text == html_file.read_text()

    stdout, stderr = process.communicate(timeout=15)
    print(stdout, stderr, sep="\n---\n")
    assert process.returncode == 0
    assert "Timeout reached." in stdout
    assert stdout.strip().endswith("Server closed.")
    with pytest.raises(requests.exceptions.ConnectionError):
        requests.get(url, timeout=5)


@pytest.mark.skipif(
    sys.platform == "win32", reason="Ctrl-C can't be sent to a child process on Windows"
)
def test_keyboard_interrupt(html_file, tmp_path):
    shutil.copy(html_file, tmp_path)
    process, url = start_quickhttp(str(tmp_path), "--port", "0", "--timeout", "1m")

    response = requests.get(url, timeout=5)
    assert response.status_code == 200

    process.send_signal(signal.SIGINT)
    stdout, stderr = process.communicate(timeout=15)
    print(stdout, stderr, sep="\n---\n")
    assert process.returncode == 0
    assert "KeyboardInterrupt received." in stdout
    assert stdout.strip().endswith("Server closed.")
    with pytest.raises(requests.exceptions.ConnectionError):
        requests.get(url, timeout=5)
