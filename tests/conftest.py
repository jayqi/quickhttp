from pathlib import Path

import pytest


@pytest.fixture()
def html_file():
    return Path(__file__).parent / "assets" / "index.html"
