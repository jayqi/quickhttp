import concurrent.futures
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
        with html_file.open("r", encoding="utf-8") as fp:
            assert response.text == fp.read()

        result = future.result()
        assert result.exit_code == 0
        assert result.stdout.strip().endswith("Server closed.")
        assert is_port_available(port)


def test_python_m_quickhttp(html_file, tmp_path):
    shutil.copy(html_file, tmp_path)
    port = find_available_port()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(
            subprocess.run,
            [
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
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        sleep(WAIT_TIME)

        response = requests.get(f"http://127.0.0.1:{port}")
        with html_file.open("r", encoding="utf-8") as fp:
            assert response.text == fp.read()

        result = future.result()
        assert result.returncode == 0
        assert result.stdout.strip().endswith("Server closed.")
        assert is_port_available(port)


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
        with html_file.open("r", encoding="utf-8") as fp:
            assert response.text == fp.read()

        result = future.result()
        assert result.exit_code == 0
        assert result.stdout.strip().endswith("Server closed.")
        assert is_port_available(port)


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
