import os
import sys
from typing import Any, Dict
from unittest.mock import MagicMock
import numpy as np
import pytest
import rasterio
import rasterio.vrt
from rasterio.transform import from_origin

from app.db import init_db
from app.services import satellite
from app.services import geospatial


@pytest.fixture(autouse=True)
def isolate_satellite_test_state():
    """Ensure in-memory SQLite tables are initialized for tests."""
    init_db()


# ---------------------------------------------------------------------------
# 1. Fallback & Defensive Satellite Tests
# ---------------------------------------------------------------------------

def test_ingest_landsat8_fallback(monkeypatch):
    """When Earth Engine credentials are unavailable, returns clean degraded unavailable response."""
    monkeypatch.delenv("EARTH_ENGINE_PROJECT", raising=False)
    # Ensure any previous mock state is cleared
    if hasattr(satellite, "ee") and getattr(satellite.ee, "data", None):
        monkeypatch.setattr(satellite.ee.data, "_initialized", False, raising=False)

    geometry = {
        "type": "Polygon",
        "coordinates": [[[72.5, 23.0], [72.6, 23.0], [72.6, 23.1], [72.5, 23.1], [72.5, 23.0]]],
    }
    result = satellite.ingest_satellite_data(
        platform="landsat8",
        start_date="2020-01-01",
        end_date="2020-01-31",
        geometry_geojson=geometry,
    )
    assert isinstance(result, dict)
    assert result["status"] == "unavailable"
    assert "credentials" in result["reason"].lower() or "unconfigured" in result["reason"].lower()
    assert "setup_instructions" in result
    assert result["metadata"]["source"] == "unavailable"
    assert result["metadata"]["synthetic"] is False
    assert result["metadata"]["resolution_m"] == 30
    assert result["indices"] is None


def test_ingest_sentinel2_fallback(monkeypatch):
    """Sentinel-2 fallback returns clean degraded response with zero mock numbers."""
    monkeypatch.delenv("EARTH_ENGINE_PROJECT", raising=False)
    if hasattr(satellite, "ee") and getattr(satellite.ee, "data", None):
        monkeypatch.setattr(satellite.ee.data, "_initialized", False, raising=False)

    geometry = {
        "type": "Polygon",
        "coordinates": [[[72.5, 23.0], [72.6, 23.0], [72.6, 23.1], [72.5, 23.1], [72.5, 23.0]]],
    }
    result = satellite.ingest_satellite_data(
        platform="sentinel2",
        start_date="2023-05-01",
        end_date="2023-05-31",
        geometry_geojson=geometry,
    )
    assert result["status"] == "unavailable"
    assert "unconfigured" in result["reason"].lower() or "credentials" in result["reason"].lower()
    assert "setup_instructions" in result
    assert result["metadata"]["source"] == "unavailable"
    assert result["metadata"]["synthetic"] is False
    assert result["metadata"]["resolution_m"] == 10
    assert result["indices"] is None


def test_ingest_modis_fallback(monkeypatch):
    """MODIS fallback returns clean degraded response with zero mock numbers."""
    monkeypatch.delenv("EARTH_ENGINE_PROJECT", raising=False)
    if hasattr(satellite, "ee") and getattr(satellite.ee, "data", None):
        monkeypatch.setattr(satellite.ee.data, "_initialized", False, raising=False)

    geometry = {
        "type": "Polygon",
        "coordinates": [[[72.5, 23.0], [72.6, 23.0], [72.6, 23.1], [72.5, 23.1], [72.5, 23.0]]],
    }
    result = satellite.ingest_satellite_data(
        platform="modis",
        start_date="2023-05-01",
        end_date="2023-05-31",
        geometry_geojson=geometry,
    )
    assert result["status"] == "unavailable"
    assert result["metadata"]["source"] == "unavailable"
    assert result["metadata"]["synthetic"] is False
    assert result["metadata"]["resolution_m"] == 1000
    assert result["indices"] is None


def test_invalid_platform_raises():
    """Unsupported platform raises a descriptive ValueError."""
    geometry = {"type": "Point", "coordinates": [0, 0]}
    with pytest.raises(ValueError, match="Unsupported platform"):
        satellite.ingest_satellite_data(
            platform="unknown_radar",
            start_date="2020-01-01",
            end_date="2020-01-31",
            geometry_geojson=geometry,
        )


def test_platform_aliases(monkeypatch):
    """Verify platform aliases route correctly."""
    monkeypatch.delenv("EARTH_ENGINE_PROJECT", raising=False)
    if hasattr(satellite, "ee") and getattr(satellite.ee, "data", None):
        monkeypatch.setattr(satellite.ee.data, "_initialized", False, raising=False)

    geometry = {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]}
    for alias in ["landsat", "landsat9", "landsat_8_9"]:
        res = satellite.ingest_satellite_data(alias, "2022-01-01", "2022-01-31", geometry)
        assert res["status"] == "unavailable"
        assert res["metadata"]["source"] == "unavailable"
        assert res["metadata"]["resolution_m"] == 30
        assert res["indices"] is None

    for alias in ["sentinel", "sentinel-2", "s2"]:
        res = satellite.ingest_satellite_data(alias, "2022-01-01", "2022-01-31", geometry)
        assert res["status"] == "unavailable"
        assert res["metadata"]["source"] == "unavailable"
        assert res["metadata"]["resolution_m"] == 10
        assert res["indices"] is None

    for alias in ["mod11a2", "modis_lst"]:
        res = satellite.ingest_satellite_data(alias, "2022-01-01", "2022-01-31", geometry)
        assert res["status"] == "unavailable"
        assert res["metadata"]["source"] == "unavailable"
        assert res["metadata"]["resolution_m"] == 1000
        assert res["indices"] is None


# ---------------------------------------------------------------------------
# 2. Mock Google Earth Engine Tests
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_earth_engine(monkeypatch):
    """Fixture providing a configurable mock Earth Engine module."""
    monkeypatch.setenv("EARTH_ENGINE_PROJECT", "mock-ee-project")
    mock_ee = MagicMock()
    mock_col = MagicMock()
    mock_img = MagicMock()

    mock_ee.Initialize = MagicMock()
    mock_ee.data._initialized = True
    mock_ee.Geometry.return_value = "mock_geom"
    mock_ee.ImageCollection.return_value = mock_col
    mock_ee.Image.return_value = mock_img

    mock_col.filterDate.return_value = mock_col
    mock_col.filterBounds.return_value = mock_col
    mock_col.filter.return_value = mock_col
    mock_col.size.return_value.getInfo.return_value = 1
    mock_col.first.return_value = mock_img

    mock_img.select.return_value = mock_img
    mock_img.multiply.return_value = mock_img
    mock_img.add.return_value = mock_img
    mock_img.subtract.return_value = mock_img
    mock_img.divide.return_value = mock_img
    mock_img.bitwiseAnd.return_value = mock_img
    mock_img.rightShift.return_value = mock_img
    mock_img.eq.return_value = mock_img
    mock_img.And.return_value = mock_img
    mock_img.gte.return_value = mock_img
    mock_img.lte.return_value = mock_img
    mock_img.updateMask.return_value = mock_img
    mock_img.normalizedDifference.return_value = mock_img
    mock_img.rename.return_value = mock_img
    mock_img.addBands.return_value = mock_img

    # Default date formatting
    mock_ee.Date.return_value.format.return_value.getInfo.return_value = "2023-06-15"
    mock_ee.Reducer.mean.return_value = "mock_reducer_mean"

    monkeypatch.setitem(sys.modules, "ee", mock_ee)
    monkeypatch.setattr(satellite, "ee", mock_ee)
    monkeypatch.setattr(satellite, "_EE_AVAILABLE", True)
    return {
        "ee": mock_ee,
        "col": mock_col,
        "img": mock_img,
    }


def test_mock_landsat8_success(mock_earth_engine):
    """Test Landsat 8 ingestion with mocked GEE returning indices and LST."""
    mock_img = mock_earth_engine["img"]
    mock_img.reduceRegion.return_value.getInfo.return_value = {
        "ndvi": 0.48,
        "ndwi": -0.22,
        "ndbi": 0.14,
        "ndbai": 0.04,
        "lst": 35.8,
    }

    geometry = {"type": "Polygon", "coordinates": [[[72.5, 23.0], [72.6, 23.0], [72.6, 23.1], [72.5, 23.1], [72.5, 23.0]]]}
    result = satellite.ingest_satellite_data("landsat8", "2023-06-01", "2023-06-30", geometry)

    assert result["metadata"]["source"] == "landsat8"
    assert result["metadata"]["synthetic"] is False
    assert result["metadata"]["acquisition_date"] == "2023-06-15"
    assert result["metadata"]["resolution_m"] == 30
    assert result["indices"]["ndvi"] == 0.48
    assert result["indices"]["ndwi"] == -0.22
    assert result["indices"]["ndbi"] == 0.14
    assert result["indices"]["ndbai"] == 0.04
    assert result["indices"]["lst"] == 35.8


def test_mock_landsat9_fallback(mock_earth_engine):
    """When Landsat 8 collection is empty, service falls back to Landsat 9."""
    mock_ee = mock_earth_engine["ee"]
    mock_col_l8 = MagicMock()
    mock_col_l8.filterDate.return_value = mock_col_l8
    mock_col_l8.filterBounds.return_value = mock_col_l8
    mock_col_l8.filter.return_value = mock_col_l8
    mock_col_l8.size.return_value.getInfo.return_value = 0  # LC08 empty!

    mock_col_l9 = MagicMock()
    mock_col_l9.filterDate.return_value = mock_col_l9
    mock_col_l9.filterBounds.return_value = mock_col_l9
    mock_col_l9.filter.return_value = mock_col_l9
    mock_col_l9.size.return_value.getInfo.return_value = 2  # LC09 available!
    mock_col_l9.first.return_value = mock_earth_engine["img"]

    def col_side_effect(col_id):
        if "LC08" in col_id:
            return mock_col_l8
        return mock_col_l9

    mock_ee.ImageCollection.side_effect = col_side_effect
    mock_earth_engine["img"].reduceRegion.return_value.getInfo.return_value = {
        "ndvi": 0.45,
        "ndwi": -0.19,
        "ndbi": 0.12,
        "ndbai": 0.03,
        "lst": 34.2,
    }

    geometry = {"type": "Polygon", "coordinates": [[[72.5, 23.0], [72.6, 23.0], [72.6, 23.1], [72.5, 23.1], [72.5, 23.0]]]}
    result = satellite.fetch_landsat8("2023-06-01", "2023-06-30", geometry)

    assert result["metadata"]["source"] == "landsat9"
    assert result["metadata"]["synthetic"] is False
    assert result["indices"]["ndvi"] == 0.45
    assert result["indices"]["lst"] == 34.2


def test_mock_landsat_all_empty_falls_back_to_synthetic(mock_earth_engine):
    """When both Landsat 8 and Landsat 9 have 0 scenes, returns clean degraded unavailable response."""
    mock_col = mock_earth_engine["col"]
    mock_col.size.return_value.getInfo.return_value = 0

    geometry = {"type": "Polygon", "coordinates": [[[72.5, 23.0], [72.6, 23.0], [72.6, 23.1], [72.5, 23.1], [72.5, 23.0]]]}
    result = satellite.fetch_landsat8("2023-06-01", "2023-06-30", geometry)

    assert result["status"] == "unavailable"
    assert result["metadata"]["synthetic"] is False
    assert result["indices"] is None
    assert "No Landsat 8 or 9 scenes available" in result["reason"]


def test_mock_sentinel2_success(mock_earth_engine):
    """Test Sentinel-2 Level-2A optical indices only (no LST / NDBaI)."""
    mock_img = mock_earth_engine["img"]
    mock_img.reduceRegion.return_value.getInfo.return_value = {
        "ndvi": 0.55,
        "ndwi": -0.16,
        "ndbi": 0.10,
    }

    geometry = {"type": "Polygon", "coordinates": [[[72.5, 23.0], [72.6, 23.0], [72.6, 23.1], [72.5, 23.1], [72.5, 23.0]]]}
    result = satellite.ingest_satellite_data("sentinel2", "2023-05-01", "2023-05-31", geometry)

    assert result["metadata"]["source"] == "sentinel2"
    assert result["metadata"]["synthetic"] is False
    assert result["metadata"]["resolution_m"] == 10
    assert result["indices"]["ndvi"] == 0.55
    assert result["indices"]["ndwi"] == -0.16
    assert result["indices"]["ndbi"] == 0.10
    assert result["indices"]["ndbai"] is None
    assert result["indices"]["lst"] is None


def test_mock_modis_lst_success(mock_earth_engine):
    """Test MODIS MOD11A2 Land Surface Temperature ingestion."""
    mock_img = mock_earth_engine["img"]
    mock_img.reduceRegion.return_value.getInfo.return_value = {
        "lst": 37.4,
    }

    geometry = {"type": "Polygon", "coordinates": [[[72.5, 23.0], [72.6, 23.0], [72.6, 23.1], [72.5, 23.1], [72.5, 23.0]]]}
    result = satellite.ingest_satellite_data("modis", "2023-05-01", "2023-05-31", geometry)

    assert result["metadata"]["source"] == "modis"
    assert result["metadata"]["synthetic"] is False
    assert result["metadata"]["resolution_m"] == 1000
    assert result["indices"]["lst"] == 37.4


def test_mock_ee_exception_triggers_fallback(mock_earth_engine):
    """Any exception during Earth Engine processing results in graceful degraded unavailable response."""
    mock_img = mock_earth_engine["img"]
    mock_img.reduceRegion.side_effect = RuntimeError("EE API Quota Exceeded")

    geometry = {"type": "Polygon", "coordinates": [[[72.5, 23.0], [72.6, 23.0], [72.6, 23.1], [72.5, 23.1], [72.5, 23.0]]]}
    result = satellite.ingest_satellite_data("landsat8", "2023-05-01", "2023-05-31", geometry)

    assert result["status"] == "unavailable"
    assert result["metadata"]["synthetic"] is False
    assert result["indices"] is None
    assert "Quota Exceeded" in result["reason"]


# ---------------------------------------------------------------------------
# 3. Geospatial Utilities Tests (geospatial.py)
# ---------------------------------------------------------------------------

def test_polygon_from_bounds():
    """Verify GeoDataFrame creation from bounding coordinates."""
    bounds = (72.5, 23.0, 72.6, 23.1)
    gdf = geospatial.polygon_from_bounds(bounds, crs="EPSG:4326")
    assert len(gdf) == 1
    assert gdf.crs == "EPSG:4326"
    poly = gdf.geometry.iloc[0]
    minx, miny, maxx, maxy = poly.bounds
    assert pytest.approx(minx) == 72.5
    assert pytest.approx(miny) == 23.0
    assert pytest.approx(maxx) == 72.6
    assert pytest.approx(maxy) == 23.1


def test_normalized_difference_and_spectral_indices():
    """Test spectral indices computation with zero-denominator safety."""
    red = np.array([0.1, 0.2, 0.0])
    nir = np.array([0.5, 0.2, 0.0])  # third element: 0+0 denominator
    green = np.array([0.3, 0.1, 0.1])
    swir = np.array([0.4, 0.3, 0.2])
    thermal = np.array([30.0, 32.0, 35.0])

    indices = geospatial.compute_spectral_indices(red, nir, green, swir, thermal)
    assert pytest.approx(indices["ndvi"][0], 0.001) == 0.6667
    assert pytest.approx(indices["ndvi"][1], 0.001) == 0.0
    assert np.isnan(indices["ndvi"][2])  # 0/0 safely returns NaN

    assert "ndwi" in indices
    assert "ndbi" in indices
    assert "ndbai" in indices


def test_landsat_lst_from_dn_and_suhii():
    """Test Landsat ST_B10 DN to Celsius conversion and SUHII calculation."""
    # ST_B10 DN 44000: 44000 * 0.00341802 + 149.0 - 273.15 = 150.39288 + 149.0 - 273.15 = 26.24288 °C
    st_dn = np.array([44000])
    qa = np.array([0], dtype=np.uint16)
    lst = geospatial.landsat_lst_from_dn(st_dn, qa)
    assert pytest.approx(lst[0], 0.01) == 26.24

    # Cloud-covered pixel (bit 3 set: 8) should be masked to NaN
    qa_cloud = np.array([8], dtype=np.uint16)
    lst_masked = geospatial.landsat_lst_from_dn(st_dn, qa_cloud)
    assert np.isnan(lst_masked[0])

    # SUHII = urban - rural
    suhii = geospatial.calculate_suhii(urban_lst=35.5, rural_reference=32.0)
    assert pytest.approx(float(suhii), 0.01) == 3.5


def test_apply_cloud_mask_array():
    """Test in-memory cloud mask application on 2D and 3D arrays."""
    arr2d = np.array([[10.0, 20.0], [30.0, 40.0]])
    mask = np.array([[False, True], [False, False]])

    masked2d = geospatial.apply_cloud_mask(arr2d, mask, nodata=-999.0)
    assert masked2d[0, 1] == -999.0
    assert masked2d[0, 0] == 10.0

    # 3D array (2 bands, 2x2)
    arr3d = np.array([
        [[10.0, 20.0], [30.0, 40.0]],
        [[100.0, 200.0], [300.0, 400.0]],
    ])
    masked3d = geospatial.apply_cloud_mask(arr3d, mask, nodata=np.nan)
    assert np.isnan(masked3d[0, 0, 1])
    assert np.isnan(masked3d[1, 0, 1])
    assert masked3d[1, 1, 1] == 400.0


def test_create_cloud_mask_landsat():
    """Test Landsat QA_PIXEL cloud bit decoding."""
    # Bit 3 = cloud (1 << 3 = 8), Bit 4 = shadow (1 << 4 = 16)
    qa = np.array([[0, 8], [16, 24]])
    mask = geospatial.create_cloud_mask_landsat(qa)
    assert not mask[0, 0]
    assert mask[0, 1]
    assert mask[1, 0]
    assert mask[1, 1]

    # Test landsat_c2_qa_mask (returns clear valid pixels)
    clear = geospatial.landsat_c2_qa_mask(qa)
    assert clear[0, 0]
    assert not clear[0, 1]
    assert not clear[1, 0]


def test_create_cloud_mask_sentinel2():
    """Test Sentinel-2 SCL class masking."""
    # Classes: 4 (vegetation, clear), 8 (cloud med prob), 9 (cloud high prob)
    scl = np.array([[4, 5], [8, 9]])
    mask = geospatial.create_cloud_mask_sentinel2(scl)
    assert not mask[0, 0]  # class 4 is clear
    assert not mask[0, 1]  # class 5 is clear
    assert mask[1, 0]      # class 8 is cloud
    assert mask[1, 1]      # class 9 is cloud


def test_reproject_and_mask_raster_file(tmp_path):
    """Test raster reprojection and cloud mask on raster files using rasterio."""
    src_file = str(tmp_path / "src.tif")
    mask_file = str(tmp_path / "mask.tif")
    dst_reproject = str(tmp_path / "reprojected.tif")
    dst_masked = str(tmp_path / "masked.tif")

    transform = from_origin(72.5, 23.5, 0.01, 0.01)
    data = np.array([[10, 20], [30, 40]], dtype=np.uint16)
    mask_data = np.array([[0, 1], [0, 0]], dtype=np.uint8)

    # Write source raster
    with rasterio.open(
        src_file,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype=data.dtype,
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data, 1)

    # Write cloud mask
    with rasterio.open(
        mask_file,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype=mask_data.dtype,
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(mask_data, 1)

    # 1. Reproject raster
    geospatial.reproject_raster(src_file, dst_reproject, dst_crs="EPSG:3857")
    with rasterio.open(dst_reproject) as r:
        assert r.crs.to_string() == "EPSG:3857"
        assert r.count == 1

    # 2. Mask clouds
    geospatial.mask_clouds(src_file, mask_file, dst_masked, nodata=0.0)
    with rasterio.open(dst_masked) as m:
        masked_arr = m.read(1)
        assert masked_arr[0, 1] == 0.0
        assert masked_arr[0, 0] == 10.0


def test_mask_clouds_dimension_mismatch_raises(tmp_path):
    """Verify mask_clouds raises ValueError when dimensions do not match."""
    src_file = str(tmp_path / "src_small.tif")
    mask_file = str(tmp_path / "mask_large.tif")
    dst_file = str(tmp_path / "out.tif")

    transform = from_origin(72.5, 23.5, 0.01, 0.01)
    with rasterio.open(src_file, "w", driver="GTiff", height=2, width=2, count=1, dtype=np.uint8, crs="EPSG:4326", transform=transform) as dst:
        dst.write(np.zeros((2, 2), dtype=np.uint8), 1)

    with rasterio.open(mask_file, "w", driver="GTiff", height=3, width=3, count=1, dtype=np.uint8, crs="EPSG:4326", transform=transform) as dst:
        dst.write(np.zeros((3, 3), dtype=np.uint8), 1)

    with pytest.raises(ValueError, match="must be identical"):
        geospatial.mask_clouds(src_file, mask_file, dst_file)


# ---------------------------------------------------------------------------
# 4. Advanced Ingestion, Radiometric Quality & Methodology Tests
# ---------------------------------------------------------------------------

def test_landsat_qa_radsat_saturation_filtering():
    """Verify Landsat QA_PIXEL bitmasking and QA_RADSAT saturation filtering."""
    st_dn = np.array([44000, 44000, 44000, 44000])
    qa_pixel = np.array([0, 0, 4, 0], dtype=np.uint16)  # pixel 2 has cirrus (bit 2)
    qa_radsat = np.array([0, 1, 0, 0], dtype=np.uint16)  # pixel 1 has radiometric saturation

    lst = geospatial.landsat_lst_from_dn(st_dn, qa_pixel=qa_pixel, qa_radsat=qa_radsat)

    # Pixel 0 is clear and unsaturated -> valid temperature
    assert pytest.approx(lst[0], 0.01) == 26.24
    # Pixel 1 has QA_RADSAT saturation -> masked to NaN
    assert np.isnan(lst[1])
    # Pixel 2 has QA_PIXEL cirrus cloud -> masked to NaN
    assert np.isnan(lst[2])
    # Pixel 3 is clear and unsaturated -> valid temperature
    assert pytest.approx(lst[3], 0.01) == 26.24


def test_validate_and_repair_geometry_cases():
    """Verify geometry validation repairs bowtie polygons and handles GeoJSON dicts."""
    # 1. Valid Polygon GeoJSON
    valid_poly = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
    }
    repaired = geospatial.validate_and_repair_geometry(valid_poly)
    assert repaired.is_valid

    # 2. Self-intersecting bowtie polygon
    bowtie = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [1.0, 1.0], [1.0, 0.0], [0.0, 1.0], [0.0, 0.0]]],
    }
    fixed = geospatial.validate_and_repair_geometry(bowtie)
    assert fixed.is_valid


def test_suhii_report_methodology():
    """Verify SUHII calculation report incorporates documented methodology and metrics."""
    urban_lsts = [38.5, 36.2, 34.0, 31.5]
    rural_ref = 32.0

    report = geospatial.calculate_suhii_report(urban_lsts, rural_reference=rural_ref)
    assert report["rural_reference_c"] == 32.0
    assert pytest.approx(report["mean_suhii"], 0.01) == 3.05
    assert pytest.approx(report["max_suhii"], 0.01) == 6.5
    assert pytest.approx(report["min_suhii"], 0.01) == -0.5
    assert report["valid_pixels"] == 4
    assert report["uhi_area_pct"] == 75.0
    assert "Surface Urban Heat Island Intensity (SUHII)" in report["methodology"]
    assert "Rural Reference" in report["methodology"]


def test_ndbai_non_commensurability_and_normalized_formula():
    """Verify NDBaI documentation caveat and MinMax normalized computation."""
    assert "NDBaI" in geospatial.NDBAI_NON_COMMENSURABILITY_CAVEAT
    assert "radiometric" in geospatial.NDBAI_NON_COMMENSURABILITY_CAVEAT.lower()

    swir = np.array([0.2, 0.4, 0.6])
    thermal_c = np.array([30.0, 35.0, 40.0])

    normalized_ndbai = geospatial.compute_ndbai_normalized(swir, thermal_c)
    assert len(normalized_ndbai) == 3
    # All values must be bounded in [-1, 1]
    assert np.all(np.isfinite(normalized_ndbai))
    assert np.all(normalized_ndbai >= -1.0)
    assert np.all(normalized_ndbai <= 1.0)


def test_sources_satellite_reexport_contract():
    """Verify sources.py cleanly re-exports satellite pipeline functions."""
    from app.services import sources

    assert sources.earth_engine is satellite.earth_engine
    assert sources.sentinel_catalog is satellite.sentinel_catalog
    assert sources.sentinel_indices is satellite.sentinel_indices
    assert sources.landsat_catalog is satellite.landsat_catalog
    assert sources.landsat_indices is satellite.landsat_indices
    assert sources.copernicus_catalog is satellite.copernicus_catalog
    assert sources.supplementary_earth_engine is satellite.supplementary_earth_engine
    assert sources.DATASET_CATALOG is satellite.DATASET_CATALOG
    assert sources.ingest_satellite_data is satellite.ingest_satellite_data


# ---------------------------------------------------------------------------
# 5. Milestone M1: Direct Landsat STAC/COG & Zonal Statistics Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_landsat_catalog_stac_discovery(monkeypatch):
    """Verify Landsat 8/9 STAC scene discovery with cloud cover filtering."""
    fake_stac_response = {
        "features": [
            {
                "id": "LC09_L2SP_148044_20240510",
                "properties": {"datetime": "2024-05-10T05:30:00Z", "eo:cloud_cover": 8.5},
            },
            {
                "id": "LC08_L2SP_148044_20240502",
                "properties": {"datetime": "2024-05-02T05:30:00Z", "eo:cloud_cover": 55.0},  # should be filtered out
            },
            {
                "id": "LC08_L2SP_148044_20240416",
                "properties": {"datetime": "2024-04-16T05:30:00Z", "eo:cloud_cover": 2.1},
            },
        ]
    }

    async def fake_get(url, params=None, headers=None):
        return fake_stac_response

    monkeypatch.setattr(satellite, "_get_json", fake_get)

    result = await satellite.landsat_catalog(23.02, 72.57, "2024-04-01", "2024-05-31")
    assert result["type"] == "FeatureCollection"
    assert result["metadata"]["source"] == "Landsat 8/9 Collection 2 L2 STAC"
    assert result["metadata"]["synthetic"] is False
    # Only scenes < 30% cloud cover retained, sorted by cloud cover
    assert len(result["features"]) == 2
    assert result["features"][0]["id"] == "LC08_L2SP_148044_20240416"  # lowest cloud cover first (2.1%)
    assert result["features"][1]["id"] == "LC09_L2SP_148044_20240510"  # 8.5%


def test_landsat_indices_stac_cog(monkeypatch):
    """Verify Landsat STAC/COG windowing, USGS thermal scaling, and spectral indices calculation."""
    # ST_B10 raw DN = 44000: 44000 * 0.00341802 + 149.0 - 273.15 = 26.24 °C
    # Surface Reflectance raw DN = 20000: 20000 * 0.0000275 - 0.2 = 0.35
    raw_st = np.full((32, 32), 44000.0)
    raw_red = np.full((32, 32), 15000.0)    # 15000 * 0.0000275 - 0.2 = 0.2125
    raw_nir = np.full((32, 32), 25000.0)    # 25000 * 0.0000275 - 0.2 = 0.4875
    raw_green = np.full((32, 32), 12000.0)  # 12000 * 0.0000275 - 0.2 = 0.13
    raw_swir = np.full((32, 32), 18000.0)   # 18000 * 0.0000275 - 0.2 = 0.295
    raw_qa = np.zeros((32, 32), dtype=np.uint16)  # clear, no clouds (bit 0..5 clear)
    raw_rad = np.zeros((32, 32), dtype=np.uint16)  # unsaturated

    band_map = {
        "lwir11": raw_st,
        "red": raw_red,
        "nir08": raw_nir,
        "green": raw_green,
        "swir16": raw_swir,
        "qa_pixel": raw_qa,
        "qa_radsat": raw_rad,
    }

    class FakeSrc:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    class FakeVRT:
        def __init__(self, src, **kwargs):
            self.key = src.key
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self, band_idx):
            return band_map[self.key]

    def fake_open(href):
        src = FakeSrc()
        src.key = href.split("/")[-1].replace(".tif", "")
        return src

    monkeypatch.setattr(rasterio, "open", fake_open)
    monkeypatch.setattr(rasterio.vrt, "WarpedVRT", FakeVRT)

    catalog = {
        "features": [
            {
                "id": "LC09_L2SP_148044_20240510",
                "properties": {"datetime": "2024-05-10T05:30:00Z"},
                "assets": {
                    "lwir11": {"href": "https://example.com/lwir11.tif"},
                    "red": {"href": "https://example.com/red.tif"},
                    "nir08": {"href": "https://example.com/nir08.tif"},
                    "green": {"href": "https://example.com/green.tif"},
                    "swir16": {"href": "https://example.com/swir16.tif"},
                    "qa_pixel": {"href": "https://example.com/qa_pixel.tif"},
                    "qa_radsat": {"href": "https://example.com/qa_radsat.tif"},
                },
            }
        ]
    }

    result = satellite.landsat_indices(catalog, 23.02, 72.57)
    assert result["source"] == "Landsat 8/9 Collection 2 L2 COG"
    assert result["synthetic"] is False
    assert result["valid_pixels"] == 32 * 32
    assert result["resolution_m"] == 30
    assert result["thermal_native_resolution_m"] == 100
    assert result["indices"]["lst"]["mean"] is not None
    # LST Celsius must be approximately 26.24 °C
    assert pytest.approx(result["indices"]["lst"]["mean"], 0.05) == 26.24
    # NDVI = (nir - red) / (nir + red) = (0.4875 - 0.2125) / (0.4875 + 0.2125) = 0.275 / 0.700 = 0.3928
    assert pytest.approx(result["indices"]["ndvi"]["mean"], 0.01) == 0.393


def test_calculate_zonal_statistics_2d():
    """Verify zonal statistics calculation across polygon zones."""
    from rasterio.transform import from_origin
    from shapely.geometry import box

    # 10x10 raster with known values: 10.0 to 100.0
    arr = np.arange(1, 101, dtype=float).reshape((10, 10))
    # Coordinates: top-left (0, 10), cell size 1.0x1.0
    transform = from_origin(0.0, 10.0, 1.0, 1.0)

    # Zone 1: covering top-left 3x3 cells (values 1..3, 11..13, 21..23)
    zone1_poly = box(0.0, 7.0, 3.0, 10.0)
    # Zone 2: covering bottom-right 2x2 cells (values 89..90, 99..100)
    zone2_poly = box(8.0, 0.0, 10.0, 2.0)

    zones = [
        {"id": "zone_1", "geometry": zone1_poly, "properties": {"name": "Top Left Ward"}},
        {"id": "zone_2", "geometry": zone2_poly, "properties": {"name": "Bottom Right Ward"}},
    ]

    stats = geospatial.calculate_zonal_statistics(
        raster_array=arr,
        transform=transform,
        crs="EPSG:4326",
        zone_geometries=zones,
    )

    assert len(stats) == 2
    z1 = stats[0]
    assert z1["zone_id"] == "zone_1"
    assert z1["stats"]["count"] == 9
    assert z1["stats"]["min"] == 1.0
    assert z1["stats"]["max"] == 23.0
    assert pytest.approx(z1["stats"]["mean"], 0.01) == 12.0
    assert pytest.approx(z1["stats"]["median"], 0.01) == 12.0

    z2 = stats[1]
    assert z2["zone_id"] == "zone_2"
    assert z2["stats"]["count"] == 4
    assert z2["stats"]["min"] == 89.0
    assert z2["stats"]["max"] == 100.0
    assert pytest.approx(z2["stats"]["mean"], 0.01) == 94.5


def test_calculate_zonal_statistics_multiband_dict():
    """Verify multi-band dictionary zonal statistics."""
    from rasterio.transform import from_origin
    from shapely.geometry import box

    lst_arr = np.full((6, 6), 35.0)
    ndvi_arr = np.full((6, 6), 0.42)
    transform = from_origin(0.0, 6.0, 1.0, 1.0)

    zones = [{"id": "w1", "geometry": box(1.0, 1.0, 4.0, 4.0)}]
    stats = geospatial.calculate_zonal_statistics(
        raster_array={"lst": lst_arr, "ndvi": ndvi_arr},
        transform=transform,
        crs="EPSG:4326",
        zone_geometries=zones,
    )

    assert len(stats) == 1
    w1_stats = stats[0]["stats"]
    assert pytest.approx(w1_stats["lst"]["mean"]) == 35.0
    assert pytest.approx(w1_stats["ndvi"]["mean"]) == 0.42
    assert w1_stats["lst"]["count"] == 9


def test_ahmedabad_amc_48_wards():
    """Verify AMC 48 municipal wards catalog and spatial coverage."""
    wards = geospatial.ahmedabad_amc_wards()
    assert len(wards) == 48
    assert wards.crs == "EPSG:4326"
    assert "zone" in wards.columns
    assert "name" in wards.columns
    zones_set = set(wards["zone"])
    assert "West" in zones_set
    assert "Central" in zones_set
    assert "East" in zones_set
    assert "South" in zones_set
    assert "North West" in zones_set
    # Check all ward polygons are valid
    assert all(geom.is_valid for geom in wards.geometry)


def test_compile_analysis_ready_dataset():
    """Verify promotion bridge creates an analysis-ready dataset satisfying state contract."""
    from app.services.state import real_dataset_ready

    dataset = geospatial.compile_analysis_ready_dataset("Ahmedabad")
    assert dataset["type"] == "FeatureCollection"
    assert dataset["metadata"]["analysis_ready"] is True
    assert dataset["metadata"]["synthetic"] is False
    assert dataset["metadata"]["city"] == "Ahmedabad"
    assert dataset["metadata"]["crs"] == "EPSG:4326"
    assert dataset["metadata"]["rural_method"] == "buffer_percentile_10"
    assert len(dataset["features"]) >= 48

    # Must pass real_dataset_ready validation contract
    assert real_dataset_ready(dataset) is True

    # Check first feature properties
    f0 = dataset["features"][0]
    props = f0["properties"]
    assert "lst" in props and isinstance(props["lst"], (int, float))
    assert "rural_reference" in props and isinstance(props["rural_reference"], (int, float))
    assert "suhii" in props
    assert "ndvi" in props
    assert "building_density" in props


def test_haversine_distance_km():
    """Verify great-circle distance calculation."""
    # Distance between Ahmedabad (23.0225, 72.5714) and Gandhinagar (23.2156, 72.6369)
    # Geodesic distance is approximately 22.4 km
    dist = geospatial.haversine_distance_km(23.0225, 72.5714, 23.2156, 72.6369)
    assert pytest.approx(dist, 0.5) == 22.4

