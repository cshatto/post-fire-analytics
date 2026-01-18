from datetime import datetime
from typing import Any

import requests


class GEDIClient:
    CMR_URL = "https://cmr.earthdata.nasa.gov/search/"
    GEDI_L1B = "GEDI01_B"
    GEDI_L2A = "GEDI02_A"
    GEDI_L2B = "GEDI02_B"
    GEDI_L4A = "GEDI04_A"

    def __init__(self, product: str = GEDI_L2A, version: str = "002") -> None:
        self.product = product
        self.version = version
        self.session = requests.Session()

    def query_granules(
        self,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
        start_date: datetime,
        end_date: datetime,
        page_size: int = 100,
        page_num: int = 1,
    ) -> dict[str, Any]:
        dt_cmr = "%Y-%m-%dT%H:%M:%SZ"
        temporal_str = f"{start_date.strftime(dt_cmr)},{end_date.strftime(dt_cmr)}"
        
        params = {
            "short_name": self.product,
            "version": self.version,
            "bounding_box": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "temporal": temporal_str,
            "page_size": page_size,
            "page_num": page_num,
        }
        response = self.session.get(f"{self.CMR_URL}granules.json", params=params)
        response.raise_for_status()
        return response.json()

    def get_download_urls(
        self,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
        start_date: datetime,
        end_date: datetime,
    ) -> list[str]:
        urls = []
        page_num = 1
        page_size = 2000
        
        while True:
            result = self.query_granules(
                min_lat, max_lat, min_lon, max_lon, start_date, end_date, page_size, page_num
            )
            entries = result.get("feed", {}).get("entry", [])
            if not entries:
                break
                
            for entry in entries:
                for link in entry.get("links", []):
                    href = link.get("href", "")
                    title = link.get("title", "")
                    if href.endswith(".h5") and title.startswith("Download"):
                        urls.append(href)
            page_num += 1
        return urls

    def get_granule_count(
        self,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
        start_date: datetime,
        end_date: datetime,
    ) -> int:
        result = self.query_granules(
            min_lat, max_lat, min_lon, max_lon, start_date, end_date, page_size=1
        )
        feed = result.get("feed", {})
        hits = feed.get("hits")
        if hits is not None:
            return int(hits)
        return len(feed.get("entry", []))
