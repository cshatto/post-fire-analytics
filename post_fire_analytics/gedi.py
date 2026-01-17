"""GEDI data query module for retrieving LiDAR data based on datetime and bounding box."""

from datetime import datetime
from typing import Any

import requests


class GEDIClient:
    CMR_SEARCH_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
    GEDI_L1B = "GEDI01_B"
    GEDI_L2A = "GEDI02_A"
    GEDI_L2B = "GEDI02_B"
    GEDI_L4A = "GEDI04_A"

    def __init__(self, product: str = GEDI_L2A) -> None:
        self.product = product
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
        params = {
            "short_name": self.product,
            "version": "002",
            "bounding_box": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "temporal": f"{start_date.isoformat()},{end_date.isoformat()}",
            "page_size": page_size,
            "page_num": page_num,
        }
        response = self.session.get(self.CMR_SEARCH_URL, params=params)
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
        max_results: int | None = None,
    ) -> list[str]:
        urls = []
        page_num = 1
        page_size = 100
        while True:
            result = self.query_granules(
                min_lat, max_lat, min_lon, max_lon, start_date, end_date, page_size, page_num
            )
            if "feed" not in result or "entry" not in result["feed"]:
                break
            entries = result["feed"]["entry"]
            if not entries:
                break
            for entry in entries:
                for link in entry.get("links", []):
                    if link.get("rel") == "http://esipfed.org/ns/fedsearch/1.1/data#":
                        urls.append(link["href"])
                if max_results and len(urls) >= max_results:
                    return urls[:max_results]
            if page_num * page_size >= len(entries):
                break
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
        return len(result.get("feed", {}).get("entry", []))
