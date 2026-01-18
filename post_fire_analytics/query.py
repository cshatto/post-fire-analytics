import datetime
from pathlib import Path
from typing import Literal

import geopandas as gpd
from cdsetool.credentials import Credentials
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
        
        self.start_date = (
            start_date if isinstance(start_date, datetime.datetime)
            else datetime.datetime.strptime(start_date, "%Y-%m-%d")
        )
        self.end_date = (
            end_date if isinstance(end_date, datetime.datetime)
            else datetime.datetime.strptime(end_date, "%Y-%m-%d")
        )
        
        self.product_type = product_type
        self.orbit_direction = orbit_direction
        self.sensor_mode = sensor_mode

    def query_by_geojson(self, geojson_path: str | Path) -> list:
        gdf = gpd.read_file(geojson_path)
        bounds = gdf.total_bounds
        bbox = [bounds[0], bounds[1], bounds[2], bounds[3]]
        logger.info(
            f"Querying Sentinel-1 for bbox: "
            f"[{bbox[0]:.4f}, {bbox[1]:.4f}, {bbox[2]:.4f}, {bbox[3]:.4f}]"
        )
        return self._query(bbox)

    def _query(self, bbox: list) -> list:
        # Format bbox as "west,south,east,north"
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
        
        features = query_features(
            collection="Sentinel1",
            search_terms=search_terms,
        )
        
        products = list(features)
        logger.info(f"Found {len(products)} Sentinel-1 products")
        
        for i, product in enumerate(products[:5], 1):
            props = product.get("properties", {})
            product_id = props.get("id", "Unknown")
            title = props.get("title", "Unknown")
            start_date = props.get("startDate", "Unknown")
            orbit_direction = props.get("orbitDirection", "Unknown")
            polarisation = props.get("polarisation", "Unknown")
            size_bytes = props.get("services", {}).get("download", {}).get("size", 0)
            
            # Convert size to human-readable format
            if size_bytes >= 1_073_741_824:  # >= 1 GB
                size_str = f"{size_bytes / 1_073_741_824:.2f} GB"
            elif size_bytes >= 1_048_576:  # >= 1 MB
                size_str = f"{size_bytes / 1_048_576:.2f} MB"
            elif size_bytes >= 1024:  # >= 1 KB
                size_str = f"{size_bytes / 1024:.2f} KB"
            else:
                size_str = f"{size_bytes} B"
            
            logger.info(
                f"  [{i}] {title} | "
                f"ID: {product_id} | "
                f"Date: {start_date} | "
                f"Orbit: {orbit_direction} | "
                f"Pol: {polarisation} | "
                f"Size: {size_str}"
            )
        
        if len(products) > 5:
            logger.info(f"  ... and {len(products) - 5} more products")
        
        return products


    def download(self, products: list) -> None:
        from cdsetool.download import download_features
        
        logger.info(f"Starting download of {len(products)} products to {self.output_dir}")
        download_features(
            features=products,
            download_dir=str(self.output_dir),
            credentials=self.credentials,
        )
        logger.success(f"Download complete. Files saved to {self.output_dir}")
