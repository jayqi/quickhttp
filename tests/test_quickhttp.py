import concurrent.futures
import platform
import shutil
import subprocess
from time import sleep

import requests
from typer.testing import CliRunner

from quickhttp.quickhttp import app
from quickhttp.core import __version__, find_available_port, is_port_available

KEEP_ALIVE_TIME = 4  # Duration to keep server alive for
WAIT_TIME = 2  # Duration to wait before running test, to give server time to start up


def test_quickhttp(html_file, tmp_path):
    shutil.copy(html_file, tmp_path)
    port = find_available_port()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(
            CliRunner().invoke,
            app,
            [
                str(tmp_path),
                "--timeout",
                f"{KEEP_ALIVE_TIME}s",
                "--port-range-min",
                port,
                "--port-range-max",
                port,
            ],
        )
        sleep(WAIT_TIME)

        response = requests.get(f"http://127.0.0.1:{port}")
        with html_file.open("r") as fp:
            # Check that server closed first so we can print results as needed for debugging
            result = future.result()
            print(result.stdout)
            assert result.exit_code == 0
            assert result.stdout.strip().endswith("Server closed.")
            assert is_port_available(port)
            # Check that response is as expected
            assert response.text == fp.read()


def test_python_m_quickhttp(html_file, tmp_path):
    shutil.copy(html_file, tmp_path)
    port = find_available_port()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        command = [
            "python",
            "-m",
            "quickhttp",
            str(tmp_path),
            "--timeout",
            f"{KEEP_ALIVE_TIME}s",
            "--port-range-min",
            str(port),
            "--port-range-max",
            str(port),
        ]
        print(command)
        future = executor.submit(
            subprocess.run,
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=platform.system() == "Windows",
        )
        sleep(WAIT_TIME)

        response = requests.get(f"http://127.0.0.1:{port}")
        with html_file.open("r") as fp:
            # Check that server closed first so we can print results as needed for debugging
            result = future.result()
            print(result.stdout)
            print(result.stderr)
            assert result.returncode == 0
            assert result.stdout.strip().endswith("Server closed.")
            assert is_port_available(port)
            # Check that response is as expected
            assert response.text == fp.read()


def test_quickhttp_with_port(html_file, tmp_path):
    shutil.copy(html_file, tmp_path)
    port = find_available_port()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(
            CliRunner().invoke,
            app,
            [str(tmp_path), "--timeout", f"{KEEP_ALIVE_TIME}s", "--port", port],
        )
        sleep(WAIT_TIME)

        response = requests.get(f"http://127.0.0.1:{port}")
        with html_file.open("r") as fp:
            # Check that server closed first so we can print results as needed for debugging
            result = future.result()
            print(result.stdout)
            assert result.exit_code == 0
            assert result.stdout.strip().endswith("Server closed.")
            assert is_port_available(port)
            # Check that response is as expected
            assert response.text == fp.read()


def test_help():
    """Test the CLI with --help flag."""
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Lightweight CLI that wraps Python's `http.server`" in result.output


def test_version():
    """Test the CLI with --version flag."""
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == __version__


def test_python_m_version():
    """Test the CLI with --version flag."""
    result = subprocess.run(
        ["python", "-m", "quickhttp", "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        shell=platform.system() == "Windows",
    )
    print(result.stdout)
    print(result.stderr)
    assert result.returncode == 0
    assert result.stdout.strip() == __version__
