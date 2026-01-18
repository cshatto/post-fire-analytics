import os
from pathlib import Path

from post_fire_analytics.query import Sentinel1Query


def test_query_by_geojson(tmp_path: Path, test_geojson: Path) -> None:
    query = Sentinel1Query(
        username=os.getenv("COPERNICUS_USERNAME"),
        password=os.getenv("COPERNICUS_PASSWORD"),
        output_dir=tmp_path,
        start_date="2022-06-19",
        end_date="2022-06-25",
    )
    
    products = query.query_by_geojson(test_geojson)
    
    assert isinstance(products, list)
    assert len(products) >= 0
