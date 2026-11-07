"""Live adapters. Remote errors are never replaced with synthetic responses."""

import os, time
import httpx
from app.db import save

_CACHE = {}


async def get_json(url, params=None, headers=None):
    key = (url, str(params))
    cached = _CACHE.get(key)
    if cached and time.monotonic() - cached[0] < 900:
        return cached[1]
    async with httpx.AsyncClient(timeout=40, follow_redirects=True) as c:
        r = await c.get(url, params=params, headers=headers)
        r.raise_for_status()
        result = r.json()
    _CACHE[key] = (time.monotonic(), result)
    return result


async def weather(lat, lon, start=None, end=None):
    variables = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,shortwave_radiation,soil_moisture_0_to_7cm"
    params = {"latitude": lat, "longitude": lon, "hourly": variables, "timezone": "UTC"}
    if start:
        params.update(start_date=start, end_date=end, models="era5_land")
    else:
        params["hourly"] = variables.replace(
            "soil_moisture_0_to_7cm", "soil_moisture_0_to_1cm"
        )
        params.update(
            forecast_days=3,
            current="temperature_2m,relative_humidity_2m,wind_speed_10m",
        )
    raw = await get_json(
        (
            "https://archive-api.open-meteo.com/v1/archive"
            if start
            else "https://api.open-meteo.com/v1/forecast"
        ),
        params,
    )
    result = {
        "source": "Open-Meteo ERA5-Land" if start else "Open-Meteo forecast",
        "synthetic": False,
        "resolution": "Weather model grid; not surface temperature",
        "data": raw,
    }
    save("weather", result)
    return result


async def osm(lat, lon):
    query = f"[out:json][timeout:25];(way(around:1000,{lat},{lon})[building];way(around:1000,{lat},{lon})[highway];way(around:1000,{lat},{lon})[leisure=park];way(around:1000,{lat},{lon})[natural=water];);out geom 120;"
    raw = await get_json("https://overpass-api.de/api/interpreter", {"data": query})
    features = []
    for e in raw.get("elements", []):
        coords = [[p["lon"], p["lat"]] for p in e.get("geometry", [])]
        if len(coords) < 2:
            continue
        closed = len(coords) > 3 and coords[0] == coords[-1]
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon" if closed else "LineString",
                    "coordinates": [coords] if closed else coords,
                },
                "properties": {"osm_id": e["id"], **e.get("tags", {})},
            }
        )
    result = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "source": "OpenStreetMap contributors / Overpass",
            "license": "ODbL",
            "synthetic": False,
            "osm_timestamp": raw.get("osm3s", {}).get("timestamp_osm_base"),
            "scope": "1 km radius; max 120 ways; partial coverage, not a density census",
        },
    }
    save("osm", result)
    return result


async def worldpop(country="IND", year=2020):
    raw = await get_json(
        "https://www.worldpop.org/rest/data/pop/wpgp", {"iso3": country}
    )
    return {
        "source": "WorldPop catalog",
        "synthetic": False,
        "datasets": [
            d
            for d in raw.get("data", [])
            if str(d.get("popyear", d.get("year", ""))) == str(year)
        ],
        "note": "Raster download and alignment required before demographic use. Age/sex and socioeconomic data are not inferred.",
    }


async def air_quality(lat, lon):
    if not os.getenv("OPENAQ_API_KEY"):
        raise ValueError("OPENAQ_API_KEY is not configured; air quality is optional.")
    return await get_json(
        "https://api.openaq.org/v3/locations",
        {"coordinates": f"{lat},{lon}", "radius": 25000, "limit": 20},
        {"X-API-Key": os.environ["OPENAQ_API_KEY"]},
    )


def earth_engine(boundary, start, end):
    import ee

    project = os.getenv("EARTH_ENGINE_PROJECT")
    if not project:
        raise ValueError(
            "EARTH_ENGINE_PROJECT and Google application credentials are required."
        )
    ee.Initialize(project=project)
    region = ee.Geometry(boundary)

    def clean(image):
        mask = (
            image.select("QA_PIXEL")
            .bitwiseAnd(63)
            .eq(0)
            .And(image.select("QA_RADSAT").eq(0))
        )
        sr = (
            image.select(
                ["SR_B3", "SR_B4", "SR_B5", "SR_B6"], ["green", "red", "nir", "swir"]
            )
            .multiply(0.0000275)
            .add(-0.2)
        )
        lst = (
            image.select("ST_B10")
            .multiply(0.00341802)
            .add(149)
            .subtract(273.15)
            .rename("lst")
        )
        return (
            sr.addBands(lst)
            .updateMask(mask)
            .copyProperties(image, ["system:time_start"])
        )

    col = (
        ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        .merge(ee.ImageCollection("LANDSAT/LC09/C02/T1_L2"))
        .filterBounds(region)
        .filterDate(start, end)
        .filter(ee.Filter.eq("PROCESSING_LEVEL", "L2SP"))
    )
    count = col.size().getInfo()
    if not count:
        raise ValueError("No Landsat scenes available for this area and date range.")
    c = col.map(clean).median()
    indices = (
        c.addBands(c.normalizedDifference(["nir", "red"]).rename("ndvi"))
        .addBands(c.normalizedDifference(["green", "nir"]).rename("ndwi"))
        .addBands(c.normalizedDifference(["swir", "nir"]).rename("ndbi"))
    )
    result = {
        "source": "Landsat 8/9 Collection 2 L2",
        "synthetic": False,
        "scene_count": count,
        "acquisition_dates_ms": col.aggregate_array("system:time_start").getInfo(),
        "crs": "EPSG:6933",
        "analysis_resolution_m": 1000,
        "thermal_native_resolution_m": 100,
        "samples": indices.sample(
            region=region,
            scale=1000,
            projection="EPSG:6933",
            numPixels=500,
            geometries=True,
            seed=42,
        ).getInfo(),
        "ndbai": None,
        "limitations": [
            "NDBaI omitted: requires radiometric normalization; reflectance and Celsius are not commensurate.",
            "No observed rural labels; not automatically fed to synthetic model.",
        ],
    }
    save("satellite", result)
    return result


DATASET_CATALOG = [
    {
        "id": "Landsat 8/9 Collection 2 L2",
        "status": "adapter implemented; credentials required",
        "resolution": "30 m product; 100 m native thermal",
    },
    {
        "id": "Sentinel-2 L2A",
        "status": "Earth Engine adapter; credentials required",
        "resolution": "10–20 m optical",
    },
    {
        "id": "MODIS MOD11A2",
        "status": "Earth Engine adapter; credentials required",
        "resolution": "1 km / 8 days",
    },
    {
        "id": "ESA WorldCover",
        "status": "Earth Engine adapter; credentials required",
        "resolution": "10 m / 2021",
    },
    {
        "id": "NASA SRTM",
        "status": "Earth Engine adapter; credentials required",
        "resolution": "30 m",
    },
    {
        "id": "GHSL / Copernicus Data Space",
        "status": "optional; not integrated",
        "resolution": "product dependent",
    },
]


async def sentinel_catalog(lat, lon, start, end):
    raw = await get_json(
        "https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items",
        {
            "bbox": f"{lon-.02},{lat-.02},{lon+.02},{lat+.02}",
            "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
            "limit": 50,
        },
    )
    features = [
        f
        for f in raw.get("features", [])
        if f["properties"].get("eo:cloud_cover", 100) < 20
    ]
    features.sort(key=lambda f: f["properties"].get("eo:cloud_cover", 100))
    result = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "source": "Element 84 Earth Search / Sentinel-2 L2A",
            "synthetic": False,
            "acquisition_dates": [f["properties"]["datetime"] for f in features],
            "resolution_m": 10,
            "crs": "Per-item projected CRS",
            "cloud_filter": "Scene cloud cover <20%; per-pixel SCL masking applied only during index processing.",
            "requested_period": [start, end],
            "scope": "Up to 50 intersecting scene footprints, not heat predictions.",
            "license": "Copernicus Sentinel data, free and open",
        },
    }
    save("satellite", result)
    return result


def sentinel_indices(catalog, lat, lon):
    """Read a bounded COG window, align every band to a common 100 m metric grid."""
    import numpy as np
    import rasterio
    from rasterio.vrt import WarpedVRT
    from rasterio.transform import from_origin
    from rasterio.enums import Resampling
    from pyproj import Transformer
    from app.services.data import spectral_indices

    if not catalog["features"]:
        raise ValueError("No scenes pass the cloud filter in this period.")
    item = catalog["features"][0]
    project = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)
    x, y = project.transform(lon, lat)
    transform = from_origin(x - 1600, y + 1600, 100, 100)
    bands = {}
    # Allow only known public COG assets returned by the trusted catalog.
    options = {
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
        "GDAL_HTTP_TIMEOUT": "25",
        "GDAL_HTTP_MAX_RETRY": "1",
    }
    if os.getenv("HTTPS_PROXY"):
        options["GDAL_HTTP_PROXY"] = os.environ["HTTPS_PROXY"]
    with rasterio.Env(**options):
        for key in ["red", "nir", "green", "swir16", "scl"]:
            href = item["assets"][key]["href"]
            if not href.startswith("https://sentinel-cogs.s3.us-west-2.amazonaws.com/"):
                raise ValueError("Unexpected satellite asset host.")
            with rasterio.open(href) as src:
                with WarpedVRT(
                    src,
                    crs="EPSG:6933",
                    transform=transform,
                    width=32,
                    height=32,
                    resampling=(
                        Resampling.nearest if key == "scl" else Resampling.average
                    ),
                ) as vrt:
                    bands[key] = vrt.read(1).astype(float)
    valid = np.isin(bands["scl"], [4, 5, 6, 7])
    for key in ["red", "nir", "green", "swir16"]:
        # STAC raster:bands documents scale and offset for this exact asset.
        metadata = item["assets"][key].get("raster:bands", [{}])[0]
        bands[key] = np.where(
            valid,
            bands[key] * metadata.get("scale", 0.0001) + metadata.get("offset", 0),
            np.nan,
        )
    indices = spectral_indices(
        bands["red"], bands["nir"], bands["green"], bands["swir16"]
    )
    result = {
        "source": "Sentinel-2 L2A COG / Earth Search",
        "synthetic": False,
        "scene_id": item["id"],
        "acquisition_date": item["properties"]["datetime"],
        "crs": "EPSG:6933",
        "resolution_m": 100,
        "shape": [32, 32],
        "transform": list(transform)[:6],
        "valid_pixels": int(valid.sum()),
        "indices": {
            k: {
                "mean": float(np.nanmean(v)) if np.isfinite(v).any() else None,
                "grid": [
                    [float(n) if np.isfinite(n) else None for n in row] for row in v
                ],
            }
            for k, v in indices.items()
        },
        "quality": "SCL classes 4,5,6,7 retained; all bands aligned to identical 100 m grid.",
        "limitations": [
            "Optical indices only. Sentinel-2 has no thermal LST band.",
            "Not passed to synthetic heat model. No validated observed-label model is available.",
        ],
    }
    save("satellite", result)
    return result


def supplementary_earth_engine(product, boundary, start, end):
    """Independent products with explicit periods/resolutions, never implicitly fused."""
    import ee

    project = os.getenv("EARTH_ENGINE_PROJECT")
    if not project:
        raise ValueError(
            "EARTH_ENGINE_PROJECT and Google application credentials are required."
        )
    ee.Initialize(project=project)
    region = ee.Geometry(boundary)
    dates = []
    if product == "sentinel":
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(region)
            .filterDate(start, end)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
        )

        def clean(image):
            scl = image.select("SCL")
            valid = scl.gte(4).And(scl.lte(7))
            return (
                image.select(["B3", "B4", "B8", "B11"], ["green", "red", "nir", "swir"])
                .multiply(0.0001)
                .updateMask(valid)
            )

        if not collection.size().getInfo():
            raise ValueError("No Sentinel-2 scenes pass cloud and date filters.")
        c = collection.map(clean).median()
        image = (
            c.normalizedDifference(["nir", "red"])
            .rename("ndvi")
            .addBands(c.normalizedDifference(["green", "nir"]).rename("ndwi"))
            .addBands(c.normalizedDifference(["swir", "nir"]).rename("ndbi"))
        )
        native = "10 m visible/NIR; 20 m SWIR/SCL"
        period = [start, end]
        dates = collection.aggregate_array("system:time_start").getInfo()
        method = "Median optical composite; SCL 4–7; no thermal band."
    elif product == "modis":
        collection = (
            ee.ImageCollection("MODIS/061/MOD11A2")
            .filterBounds(region)
            .filterDate(start, end)
        )

        def clean(image):
            qc = image.select("QC_Day")
            mask = qc.bitwiseAnd(3).eq(0).And(qc.rightShift(6).bitwiseAnd(3).lte(1))
            return (
                image.select("LST_Day_1km")
                .multiply(0.02)
                .subtract(273.15)
                .rename("lst")
                .updateMask(mask)
            )

        if not collection.size().getInfo():
            raise ValueError("No MODIS composites in the date range.")
        image = collection.map(clean).mean()
        native = "1 km / 8-day composites"
        period = [start, end]
        dates = collection.aggregate_array("system:time_start").getInfo()
        method = "Mean of quality-filtered daytime eight-day composites; not simultaneous with Landsat."
    elif product == "worldcover":
        image = (
            ee.ImageCollection("ESA/WorldCover/v200")
            .first()
            .select("Map")
            .rename("land_cover")
        )
        native = "10 m"
        period = ["2021-01-01", "2021-12-31"]
        method = "Categorical center sampling, not aggregated fractions."
    elif product == "srtm":
        image = ee.Image("USGS/SRTMGL1_003").select("elevation")
        native = "30 m"
        period = ["2000-02-11", "2000-02-22"]
        method = "Elevation sampling in metres; historical terrain baseline."
    else:
        raise ValueError("Unknown satellite product.")
    result = {
        "source": product,
        "synthetic": False,
        "native_resolution": native,
        "observation_period": period,
        "acquisition_dates_ms": dates,
        "crs": "EPSG:6933",
        "analysis_resolution_m": 1000,
        "method": method,
        "samples": image.sample(
            region=region,
            projection="EPSG:6933",
            scale=1000,
            numPixels=500,
            geometries=True,
            seed=42,
        ).getInfo(),
        "limitations": [
            "Product retained separately; resampling does not create finer native information.",
            "No automatic fusion across observation periods or spatial resolutions.",
        ],
    }
    save("satellite", result)
    return result
