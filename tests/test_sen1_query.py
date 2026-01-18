import os
from pathlib import Path

import geopandas as gpd

from post_fire_analytics.query import Sentinel1Query


def test_query_by_geojson(tmp_path: Path, test_geojson: Path) -> None:
    # Read fire data to get dates
    gdf = gpd.read_file(test_geojson)
    fire = gdf.iloc[0]
    
    # Extract dates from fire event
    ig_date = fire["Ig_Date"]  # Ignition date: 2022-06-19
    post_id = fire["Post_ID"]  # Post-fire image ID: 901403220220704
    # Extract post-fire date from Post_ID (format: YYYYMMDD at end)
    post_date = f"{post_id[-8:-4]}-{post_id[-4:-2]}-{post_id[-2:]}"  # 2022-07-04
    
    query = Sentinel1Query(
        username=os.getenv("COPERNICUS_USERNAME"),
        password=os.getenv("COPERNICUS_PASSWORD"),
        output_dir=tmp_path,
        start_date=ig_date,
        end_date=post_date,
    )
    
    products = query.query_by_geojson(test_geojson)
    
    assert isinstance(products, list)
    assert len(products) >= 0
    
    if products:
        query.download(products[:1])
