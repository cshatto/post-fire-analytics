from pathlib import Path

from post_fire_analytics.preprocess import Sentinel1Preprocessor


def test_preprocess_pipeline(sentinel1_image: Path, tmp_path: Path, test_geojson: Path) -> None:
    """Test complete Sentinel-1 preprocessing pipeline."""
    preprocessor = Sentinel1Preprocessor(sentinel1_image)
    
    # Load VV band
    vv = preprocessor.load_band(polarization="VV")
    calibrated = preprocessor.calibrate(vv, calibration="sigma0")
    db_data = preprocessor.to_db(calibrated)
    filtered = preprocessor.apply_speckle_filter(db_data, filter_type="lee", window_size=5)
    clipped = preprocessor.clip_to_geojson(filtered, test_geojson)
    assert clipped.shape != filtered.shape  # Should be cropped
    assert clipped.shape[0] <= 2000  # Should be smaller
    assert clipped.shape[1] <= 2000
    assert "cropped" in clipped.attrs
    
    # Save to file
    output_file = Path("processed_vv_clipped.tif")
    preprocessor.save(clipped, output_file)
    assert output_file.exists()

