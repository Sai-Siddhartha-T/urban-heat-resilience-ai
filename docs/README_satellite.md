# Satellite Data and Earth Observation Ingestion

This document details the architecture, Earth Observation (EO) ingestion pipelines, geospatial raster handling utilities, and testing strategies implemented in the Heatwise platform.

---

## 1. Architecture & Services

The satellite ingestion pipeline consists of two primary service modules:

### `backend/app/services/geospatial.py`
High-performance raster and vector processing utilities built on top of `rasterio`, `geopandas`, and `shapely`:
- **Raster Reprojection**: `reproject_raster` reprojects GeoTIFF and other raster formats to any target CRS (e.g., EPSG:4326, EPSG:3857, EPSG:6933) with configurable resampling methods (`nearest`, `bilinear`, `cubic`).
- **Cloud Masking**:
  - `mask_clouds`: File-based cloud masking replacing cloud-affected pixels with `nodata`.
  - `apply_cloud_mask`: In-memory masking for 2D and 3D numpy arrays.
  - `create_cloud_mask_landsat`: Decodes Landsat Collection 2 QA_PIXEL bitmasks (dilated cloud, high-confidence cloud, cloud shadow, snow/ice).
  - `landsat_c2_qa_mask`: Validates clear pixels using bits 0–5 (mask value 63) and `QA_RADSAT` saturation flags.
  - `create_cloud_mask_sentinel2`: Filters cloudy pixels using Sentinel-2 Scene Classification Layer (SCL) classes (shadows, medium/high probability clouds, thin cirrus).
- **Vector Operations**:
  - `polygon_from_bounds`: Constructs a `geopandas.GeoDataFrame` from bounding coordinates `(minx, miny, maxx, maxy)`.
  - `validate_and_repair_geometry`: Validates and repairs topological anomalies in polygons via `shapely.validation.make_valid`.
  - `clip_raster_by_geometry`: Clips and crops raster datasets to vector boundaries using `rasterio.mask.mask`.
- **Spectral Indices & Thermal Processing**:
  - `normalized_difference`: Zero-denominator safe division $(a - b) / (a + b)$ returning `np.nan` for zero/degenerate denominators.
  - `compute_spectral_indices`: Computes NDVI, NDWI, NDBI, and NDBaI from raw band arrays.
  - `landsat_lst_from_dn`: Converts Landsat Collection 2 ST_B10 digital numbers directly to Land Surface Temperature in Celsius ($\text{DN} \times 0.00341802 + 149.0 - 273.15$) with QA_PIXEL masking.
  - `calculate_suhii`: Computes Surface Urban Heat Island Intensity ($\text{LST}_{\text{urban}} - \text{LST}_{\text{rural}}$).

### `backend/app/services/satellite.py`
Google Earth Engine (GEE) integration service with graceful fallback:
- **Landsat 8/9 Level-2**:
  - Primary collection: `LANDSAT/LC08/C02/T1_L2` (Landsat 8)
  - Secondary fallback: `LANDSAT/LC09/C02/T1_L2` (Landsat 9)
  - Scale factors: Surface Reflectance $\times 0.0000275 - 0.2$; Thermal ST_B10 $\times 0.00341802 + 149.0 - 273.15$ (°C).
  - QA filtering: Bits 0–5 of `QA_PIXEL` and `QA_RADSAT` saturation filter.
  - Computes: LST, NDVI, NDWI, NDBI, and NDBaI.
- **Sentinel-2 Level-2A (Optical Only)**:
  - Collection: `COPERNICUS/S2_SR_HARMONIZED`
  - Scale factor: $\times 0.0001$
  - Cloud filter: `CLOUDY_PIXEL_PERCENTAGE < 30` and SCL valid classes 4–7.
  - Computes: NDVI, NDWI, NDBI.
  - **Thermal Note**: Sentinel-2 MultiSpectral Instrument (MSI) has no thermal band; `lst` and `ndbai` are explicitly set to `None`.
- **MODIS MOD11A2 (Optional)**:
  - Collection: `MODIS/061/MOD11A2` (8-day composite at 1 km).
  - LST scaling: $\text{DN} \times 0.02 - 273.15$ (°C).
  - Quality mask: `QC_Day` bitmask filtering.

---

## 2. Spectral Indices & Physics Caveats

| Index | Formula | Satellite Bands | Description |
|---|---|---|---|
| **NDVI** | $\frac{\text{NIR} - \text{Red}}{\text{NIR} + \text{Red}}$ | Landsat: B5/B4; Sentinel-2: B8/B4 | Normalized Difference Vegetation Index |
| **NDWI** | $\frac{\text{Green} - \text{NIR}}{\text{Green} + \text{NIR}}$ | Landsat: B3/B5; Sentinel-2: B3/B8 | Normalized Difference Water Index (McFeeters) |
| **NDBI** | $\frac{\text{SWIR} - \text{NIR}}{\text{SWIR} + \text{NIR}}$ | Landsat: B6/B5; Sentinel-2: B11/B8 | Normalized Difference Built-Up Index |
| **NDBaI** | $\frac{\text{SWIR} - \text{Thermal}}{\text{SWIR} + \text{Thermal}}$ | Landsat: B6/B10; Sentinel-2: *N/A* | Normalized Difference Bareness / Built-up area Index |
| **LST** | $\text{ST\_B10} \times 0.00341802 - 124.15$ | Landsat: ST_B10; MODIS: LST_Day_1km | Land Surface Temperature in °C |

> [!WARNING]
> **NDBaI Radiometric Non-Commensurability Caveat**:
> NDBaI requires commensurate radiometric normalization between surface reflectance (unitless, 0–1) and thermal emission (radiance or Kelvin). It cannot be computed simply from raw reflectance and Celsius. When thermal bands are unavailable (Sentinel-2), NDBaI is omitted (`None`).

---

## 3. Metadata Storage & Synthetic Fallback

Every satellite ingestion response contains standardized `metadata` and `indices` structures:

```json
{
  "metadata": {
    "source": "landsat8",
    "synthetic": false,
    "platform": "landsat8",
    "acquisition_date": "2023-06-15",
    "resolution_m": 30
  },
  "indices": {
    "ndvi": 0.48,
    "ndwi": -0.22,
    "ndbi": 0.14,
    "ndbai": 0.04,
    "lst": 35.8
  }
}
```

### Synthetic Data Fallback Label
When Google Earth Engine is unauthenticated, the SDK is unavailable, network timeouts occur, or no scenes intersect the query extent, the system gracefully returns an explicitly labelled fallback payload:
- `metadata.source`: `"synthetic"`
- `metadata.synthetic`: `true`
- `metadata.fallback_reason`: Descriptive error message indicating why the live satellite feed was substituted
- `metadata.acquisition_date`: Populated with the requested start date
- `metadata.resolution_m`: Native platform resolution (30m for Landsat, 10m for Sentinel-2, 1000m for MODIS)
- `indices`: Deterministic baseline values ensuring downstream analytics pipelines continue operating without unhandled exceptions.

---

## 4. Usage Examples

### Fetching Satellite Data via Python API

```python
from app.services import satellite

area_of_interest = {
    "type": "Polygon",
    "coordinates": [[[72.50, 23.00], [72.60, 23.00], [72.60, 23.10], [72.50, 23.10], [72.50, 23.00]]]
}

# Landsat 8/9 with LST and optical indices
landsat_data = satellite.ingest_satellite_data(
    platform="landsat8",
    start_date="2023-05-01",
    end_date="2023-05-31",
    geometry_geojson=area_of_interest,
)
print("Landsat LST:", landsat_data["indices"]["lst"])

# Sentinel-2 optical indices
sentinel_data = satellite.ingest_satellite_data(
    platform="sentinel2",
    start_date="2023-05-01",
    end_date="2023-05-31",
    geometry_geojson=area_of_interest,
)
print("Sentinel NDVI:", sentinel_data["indices"]["ndvi"])
```

### Reprojecting and Cloud Masking Rasters

```python
from app.services import geospatial

# Reproject WGS84 GeoTIFF to EPSG:3857 (Web Mercator)
geospatial.reproject_raster("input_wgs84.tif", "output_mercator.tif", dst_crs="EPSG:3857")

# Apply binary cloud mask to a scene
geospatial.mask_clouds("scene.tif", "cloud_mask.tif", "cloud_free.tif", nodata=-9999.0)
```

---

## 5. Testing & Verification

Unit tests are located under `backend/tests/test_satellite.py`:
- **Mock Earth Engine Verification**: Fully mocks the Earth Engine Python API (`ee.ImageCollection`, `ee.Image`, `ee.Geometry`, `ee.Reducer`, `ee.Date`) using `unittest.mock.MagicMock` to verify Landsat 8, Landsat 9 fallback, Sentinel-2 optical indices, and MODIS LST pipelines without external network dependencies.
- **Defensive Fallback Verification**: Tests environment variable isolation (`EARTH_ENGINE_PROJECT` deletion and uninitialized GEE states) to prove synthetic fallback labelling and reason propagation.
- **Geospatial Utilities Verification**: Tests in-memory and file-based raster reprojection, cloud masking, Landsat QA bitmask decoding, Sentinel-2 SCL class filtering, and bounding box polygon generation.
