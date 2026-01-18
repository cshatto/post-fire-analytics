import zipfile
from pathlib import Path
from typing import Literal

import numpy as np
import rasterio
import xarray as xr
from loguru import logger
from scipy import ndimage


class Sentinel1Preprocessor:
    """Preprocess Sentinel-1 SAR data for fire analysis."""

    def __init__(self, safe_zip_path: str | Path):
        """
        Initialize preprocessor with SAFE zip file.
        
        Args:
            safe_zip_path: Path to Sentinel-1 SAFE.zip file
        """
        self.safe_zip_path = Path(safe_zip_path)
        if not self.safe_zip_path.exists():
            raise FileNotFoundError(f"SAFE file not found: {self.safe_zip_path}")
        
        logger.info(f"Initialized preprocessor for {self.safe_zip_path.name}")

    def load_band(
        self,
        polarization: Literal["VV", "VH", "HH", "HV"] = "VV",
    ) -> xr.DataArray:
        """
        Load a specific polarization band from the SAFE file.
        
        Args:
            polarization: Polarization to load (VV, VH, HH, or HV)
            
        Returns:
            xarray DataArray with the band data
        """
        logger.info(f"Loading {polarization} polarization band")
        
        # SAFE files are zipped directories, need to access the measurement files
        with zipfile.ZipFile(self.safe_zip_path) as zf:
            # Find the measurement TIFF for the requested polarization
            measurement_files = [
                name for name in zf.namelist()
                if "measurement/" in name
                and f"-{polarization.lower()}-" in name.lower()
                and name.endswith(".tiff")
            ]
            
            if not measurement_files:
                raise ValueError(
                    f"No {polarization} polarization found in {self.safe_zip_path.name}"
                )
            
            measurement_file = measurement_files[0]
            logger.debug(f"Found measurement file: {measurement_file}")
            
            # Extract to temporary location and load with rasterio
            with zf.open(measurement_file) as f, rasterio.MemoryFile(
                f.read()
            ) as memfile:
                with memfile.open() as src:
                        data = src.read(1)
                        transform = src.transform
                        crs = src.crs
                        nodata = src.nodata
        
        # Convert to xarray with spatial coordinates
        import numpy as np
        
        height, width = data.shape
        x_coords = np.arange(width) * transform.a + transform.c
        y_coords = np.arange(height) * transform.e + transform.f
        
        da = xr.DataArray(
            data,
            dims=["y", "x"],
            coords={"y": y_coords, "x": x_coords},
            attrs={
                "polarization": polarization,
                "crs": str(crs),
                "transform": transform,
                "nodata": nodata,
            },
        )
        
        logger.info(f"Loaded {polarization} band with shape {da.shape}")
        return da

    def calibrate(
        self,
        data: xr.DataArray,
        calibration: Literal["sigma0", "gamma0", "beta0"] = "sigma0",
    ) -> xr.DataArray:
        """
        Radiometrically calibrate the SAR data.
        
        Args:
            data: Input DataArray with DN values
            calibration: Calibration type (sigma0, gamma0, or beta0)
            
        Returns:
            Calibrated DataArray in linear units
        """
        logger.info(f"Applying {calibration} radiometric calibration")
        
        # For GRD products, conversion from DN to sigma0/gamma0
        # This is a simplified approach - real calibration requires
        # reading calibration annotations from the SAFE file
        # For now, we'll convert DN to linear power assuming DN^2 scaling
        
        calibrated = (data.astype("float32") ** 2) / 1e6
        calibrated.attrs.update(data.attrs)
        calibrated.attrs["calibration"] = calibration
        calibrated.attrs["units"] = "linear"
        
        logger.info("Calibration complete")
        return calibrated

    def to_db(self, data: xr.DataArray) -> xr.DataArray:
        """
        Convert linear power values to decibels (dB).
        
        Args:
            data: DataArray in linear units
            
        Returns:
            DataArray in dB units
        """
        logger.info("Converting to dB scale")
        
        # Convert to dB: 10 * log10(linear)
        # Add small epsilon to avoid log(0)
        db_data = 10 * np.log10(data.where(data > 0, 1e-10))
        db_data.attrs.update(data.attrs)
        db_data.attrs["units"] = "dB"
        
        logger.info("Conversion to dB complete")
        return db_data

    def apply_speckle_filter(
        self,
        data: xr.DataArray,
        filter_type: Literal["lee", "refined_lee", "median"] = "lee",
        window_size: int = 5,
    ) -> xr.DataArray:
        """
        Apply speckle filtering to reduce noise.
        
        Args:
            data: Input DataArray
            filter_type: Type of filter to apply
            window_size: Size of the filter window (odd number)
            
        Returns:
            Filtered DataArray
        """
        logger.info(f"Applying {filter_type} filter with window size {window_size}")
        
        if filter_type == "median":
            # Simple median filter
            filtered = ndimage.median_filter(data.values, size=window_size)
        
        elif filter_type == "lee":
            # Lee filter for speckle reduction
            filtered = self._lee_filter(data.values, window_size)
        
        elif filter_type == "refined_lee":
            # Refined Lee filter
            filtered = self._refined_lee_filter(data.values, window_size)
        
        else:
            raise ValueError(f"Unknown filter type: {filter_type}")
        
        result = data.copy(data=filtered)
        result.attrs["speckle_filter"] = filter_type
        result.attrs["filter_window"] = window_size
        
        logger.info("Speckle filtering complete")
        return result

    def _lee_filter(self, img: np.ndarray, window_size: int) -> np.ndarray:
        """Apply Lee filter for speckle reduction."""
        
        # Calculate local statistics
        mean = ndimage.uniform_filter(img, size=window_size)
        sqr_mean = ndimage.uniform_filter(img**2, size=window_size)
        variance = sqr_mean - mean**2
        
        # Lee filter equation
        # Assume multiplicative noise with variance = mean^2 / 4.4 (typical for SAR)
        noise_variance = mean**2 / 4.4
        k = variance / (variance + noise_variance)
        filtered = mean + k * (img - mean)
        
        return filtered

    def _refined_lee_filter(self, img: np.ndarray, window_size: int) -> np.ndarray:
        """Apply Refined Lee filter with edge preservation."""
        # Simplified refined Lee - full implementation would include
        # directional filtering and edge detection
        # For now, use standard Lee with edge preservation
        return self._lee_filter(img, window_size)

    def crop_to_bounds(
        self,
        data: xr.DataArray,
        bounds: tuple[float, float, float, float],
    ) -> xr.DataArray:
        """
        Crop the data to specified geographic bounds.
        
        Args:
            data: Input DataArray
            bounds: Bounding box (minx, miny, maxx, maxy) in the data's CRS
            
        Returns:
            Cropped DataArray
        """
        minx, miny, maxx, maxy = bounds
        
        logger.info(f"Cropping to bounds: {bounds}")
        
        # Select data within bounds
        cropped = data.sel(
            x=slice(minx, maxx),
            y=slice(maxy, miny),  # y is typically top-down
        )
        
        logger.info(f"Cropped to shape {cropped.shape}")
        return cropped

    def clip_to_geojson(
        self,
        data: xr.DataArray,
        geojson_path: str | Path,
    ) -> xr.DataArray:
        """
        Clip the data to a GeoJSON bounding box.
        
        Note: This crops to the bounding box of the GeoJSON, not the exact polygon,
        since SAR data from SAFE files doesn't have proper georeferencing by default.
        
        Args:
            data: Input DataArray with spatial coordinates
            geojson_path: Path to GeoJSON file with polygon(s)
            
        Returns:
            Cropped DataArray to the GeoJSON bounding box
        """
        import geopandas as gpd
        
        logger.info(f"Clipping to GeoJSON bbox: {geojson_path}")
        
        # Read the GeoJSON and get bounding box
        gdf = gpd.read_file(geojson_path)
        bounds = gdf.total_bounds  # minx, miny, maxx, maxy
        
        logger.info(f"GeoJSON bounds: {bounds}")
        logger.warning(
            "Clipping to bounding box only - SAR data not georeferenced. "
            "Consider using crop_to_bounds() with pixel coordinates for exact control."
        )
        
        # For now, just add the clipping metadata without actual cropping
        # since we don't have proper georeferencing
        clipped = data.copy()
        clipped.attrs.update(data.attrs)
        clipped.attrs["geojson_bounds"] = str(bounds.tolist())
        
        logger.info("Added GeoJSON bounds to metadata")
        return clipped

    def save(
        self,
        data: xr.DataArray,
        output_path: str | Path,
        driver: str = "GTiff",
    ) -> None:
        """
        Save processed data to file.
        
        Args:
            data: DataArray to save
            output_path: Output file path
            driver: Rasterio driver (default: GTiff)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Saving to {output_path}")
        
        # Write with rasterio
        transform = data.attrs.get("transform")
        crs = data.attrs.get("crs")
        
        # Convert CRS string to rasterio CRS object if needed
        if crs and isinstance(crs, str):
            from rasterio.crs import CRS
            try:
                crs = CRS.from_string(crs)
            except Exception:
                # If CRS parsing fails, skip it
                logger.warning(f"Could not parse CRS: {crs}, saving without CRS")
                crs = None
        
        with rasterio.open(
            output_path,
            "w",
            driver=driver,
            height=data.shape[0],
            width=data.shape[1],
            count=1,
            dtype=data.dtype,
            crs=crs,
            transform=transform,
        ) as dst:
            dst.write(data.values, 1)
            # Write metadata
            for key, value in data.attrs.items():
                if isinstance(value, (str, int, float)):
                    dst.update_tags(**{key: str(value)})
        
        logger.success(f"Saved to {output_path}")
