from pathlib import Path

import pytest


@pytest.fixture
def test_geojson() -> Path:
    return Path(__file__).parent / "assets" / "test_fire.geojson"


@pytest.fixture(autouse=True)
def copernicus_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COPERNICUS_USERNAME", "shatto.cj@gmail.com")
    monkeypatch.setenv("COPERNICUS_PASSWORD", "2J.!NVtJ+vPPFg3")
