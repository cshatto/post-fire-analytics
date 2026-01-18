from pathlib import Path

import pytest


@pytest.fixture
def test_geojson() -> Path:
    return Path(__file__).parent / "assets" / "test_fire.geojson"


@pytest.fixture
def sentinel1_image() -> Path:
    """Path to the downloaded Sentinel-1 test image."""
    return (
        Path(__file__).parent
        / "assets"
        / "S1A_IW_GRDH_1SDV_20220620T225926_20220620T225951_043753_053941_5399.SAFE.zip"
    )


@pytest.fixture(autouse=True)
def copernicus_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COPERNICUS_USERNAME", "shatto.cj@gmail.com")
    monkeypatch.setenv("COPERNICUS_PASSWORD", "2J.!NVtJ+vPPFg3")
