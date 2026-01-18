from datetime import datetime

import geopandas as gpd
from loguru import logger

from post_fire_analytics.gedi import GEDIClient


def test_query_first_fire() -> None:
    gdf = gpd.read_file("tests/assets/mtbs_perims_2022.geojson")
    fire = gdf.iloc[0]
    bounds = fire.geometry.bounds
    ig_date = datetime.fromisoformat(str(fire["Ig_Date"]).replace("Z", ""))
    start_date = ig_date
    end_date = datetime(ig_date.year, 12, 31)
    client = GEDIClient(product=GEDIClient.GEDI_L2A)
    logger.info(f"Querying fire: {fire['Incid_Name']}")
    logger.info(f"Bounds: {bounds}")
    logger.info(f"Date range: {start_date.date()} to {end_date.date()}")
    count = client.get_granule_count(
        bounds[1], bounds[3], bounds[0], bounds[2], start_date, end_date
    )
    logger.info(f"Granules found: {count}")
    assert isinstance(count, int)
    assert count >= 0
