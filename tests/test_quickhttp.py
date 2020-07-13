import concurrent.futures
import shutil
import subprocess

import requests
from typer.testing import CliRunner

from quickhttp.quickhttp import app
from quickhttp.core import __version__, find_available_port


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


def test_command_python_m_version():
    """Test the CLI using python -m invocation.
    """
    result = subprocess.run(
        ["python", "-m", "quickhttp", "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == __version__


def test_main_auto(html_file, tmp_path):
    shutil.copy(html_file, tmp_path)
    port = find_available_port()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(
            CliRunner().invoke,
            app,
            [str(tmp_path), "--port-range-min", port, "--port-range-max", port, "--time", "3s"],
        )

        response = requests.get(f"http://127.0.0.1:{port}")
        with html_file.open("r") as fp:
            assert response.text == fp.read()

        result = future.result()
        assert result.exit_code == 0
        assert result.stdout.strip().endswith("Server closed.")
