import datetime
from pathlib import Path
from typing import Any, Literal

import geopandas as gpd
from cdsetool.credentials import Credentials
from cdsetool.download import download_features
from cdsetool.query import query_features
from loguru import logger


class Sentinel1Query:
    def __init__(
        self,
        username: str,
        password: str,
        output_dir: str | Path,
        start_date: str | datetime.datetime,
        end_date: str | datetime.datetime,
        product_type: Literal["GRD", "SLC", "OCN"] = "GRD",
        orbit_direction: Literal["ASCENDING", "DESCENDING"] | None = None,
        sensor_mode: Literal["SM", "IW", "EW", "WV"] = "IW",
    ):
        self.credentials = Credentials(username, password)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.start_date = self._parse_date(start_date)
        self.end_date = self._parse_date(end_date)
        self.product_type = product_type
        self.orbit_direction = orbit_direction
        self.sensor_mode = sensor_mode

    @staticmethod
    def _parse_date(date: str | datetime.datetime) -> datetime.datetime:
        return (
            date if isinstance(date, datetime.datetime)
            else datetime.datetime.strptime(date, "%Y-%m-%d")
        )

    def query_by_geojson(self, geojson_path: str | Path) -> list[dict[str, Any]]:
        bounds = gpd.read_file(geojson_path).total_bounds
        logger.info(
            f"Querying Sentinel-1 for bbox: "
            f"[{bounds[0]:.4f}, {bounds[1]:.4f}, {bounds[2]:.4f}, {bounds[3]:.4f}]"
        )
        return self._query(bounds.tolist())

    def _query(self, bbox: list[float]) -> list[dict[str, Any]]:
        # Format bbox as comma-separated string: "west,south,east,north"
        box_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
        
        search_terms = {
            "box": box_str,
            "startDate": self.start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "completionDate": self.end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "productType": self.product_type,
            "sensorMode": self.sensor_mode,
        }
        if self.orbit_direction:
            search_terms["orbitDirection"] = self.orbit_direction

        products = list(query_features(collection="Sentinel1", search_terms=search_terms))
        logger.info(f"Found {len(products)} Sentinel-1 products")

        for i, product in enumerate(products[:5], 1):
            props = product.get("properties", {})
            logger.info(
                f"  [{i}] {props.get('title', 'Unknown')} | "
                f"ID: {props.get('id', 'Unknown')} | "
                f"Date: {props.get('startDate', 'Unknown')} | "
                f"Orbit: {props.get('orbitDirection', 'Unknown')} | "
                f"Pol: {props.get('polarisation', 'Unknown')}"
            )

        if len(products) > 5:
            logger.info(f"  ... and {len(products) - 5} more products")

        return products

    def download(self, products: list[dict[str, Any]]) -> None:
        logger.info(f"Starting download of {len(products)} products to {self.output_dir}")
        options = {"credentials": self.credentials}
        for _ in download_features(features=products, path=str(self.output_dir), options=options):
            pass
        logger.success(f"Download complete. Files saved to {self.output_dir}")
