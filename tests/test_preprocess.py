from pathlib import Path

from post_fire_analytics.preprocess import Sentinel1Preprocessor


def test_preprocess_pipeline(sentinel1_image: Path, tmp_path: Path, test_geojson: Path) -> None:
    """Test complete Sentinel-1 preprocessing pipeline."""
    preprocessor = Sentinel1Preprocessor(sentinel1_image)
    
    # Load VV band
    vv = preprocessor.load_band(polarization="VV")
    assert vv.dims == ("y", "x")
    assert vv.attrs["polarization"] == "VV"
    
    # Calibrate to sigma0
    calibrated = preprocessor.calibrate(vv, calibration="sigma0")
    assert calibrated.attrs["calibration"] == "sigma0"
    assert calibrated.attrs["units"] == "linear"
    
    # Convert to dB
    db_data = preprocessor.to_db(calibrated)
    assert db_data.attrs["units"] == "dB"
    assert db_data.mean().values < 0  # Backscatter is typically negative
    
    # Apply Lee speckle filter
    filtered = preprocessor.apply_speckle_filter(db_data, filter_type="lee", window_size=5)
    assert filtered.shape == db_data.shape
    assert filtered.attrs["speckle_filter"] == "lee"
    
    # Clip to GeoJSON polygon
    clipped = preprocessor.clip_to_geojson(filtered, test_geojson)
    assert clipped.shape != filtered.shape  # Should be cropped
    assert clipped.shape[0] <= 2000  # Should be smaller
    assert clipped.shape[1] <= 2000
    assert "cropped" in clipped.attrs
    
    # Save to file
    output_file = tmp_path / "processed_vv_clipped.tif"
    preprocessor.save(clipped, output_file)
    assert output_file.exists()

