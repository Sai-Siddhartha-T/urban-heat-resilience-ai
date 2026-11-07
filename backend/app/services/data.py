import math
from datetime import datetime, timezone
import numpy as np
from shapely.geometry import Polygon, shape, mapping
from sqlalchemy.orm import Session
from app.db import Zone, engine, POSTGIS, save

CITIES = {
    "Ahmedabad": (23.0225, 72.5714),
    "Delhi": (28.6139, 77.2090),
    "Hyderabad": (17.3850, 78.4867),
}
FEATURES = [
    "ndvi",
    "ndwi",
    "ndbi",
    "ndbai",
    "building_density",
    "population_density",
    "air_temperature",
    "humidity",
    "rainfall",
    "solar_radiation",
    "soil_moisture",
    "land_cover",
]


def sample_data(
    city="Ahmedabad", lat=None, lon=None, boundary=None, rural_reference=33.0
):
    """Deterministic synthetic landscape for software verification, never observations."""
    lat, lon = (lat, lon) if lat is not None and lon is not None else CITIES[city]
    rng = np.random.default_rng(42)
    zones = []
    width = 0.009 / math.cos(math.radians(lat))
    height = 0.009
    for y in range(18):
        for x in range(18):
            west = lon + (x - 9) * width
            south = lat + (y - 9) * height
            polygon = Polygon(
                [
                    (west, south),
                    (west + width, south),
                    (west + width, south + height),
                    (west, south + height),
                    (west, south),
                ]
            )
            if boundary and not shape(boundary).covers(polygon.centroid):
                continue
            built = float(rng.uniform(0.18, 0.91))
            ndvi = float(np.clip(0.85 - 0.7 * built + rng.normal(0, 0.11), 0.03, 0.85))
            ndwi = float(rng.uniform(-0.55, 0.2))
            ndbi = float(built - 0.5 + rng.normal(0, 0.06))
            ndbai = float(rng.uniform(-0.3, 0.4))
            air = float(rng.uniform(29, 38))
            humidity = float(rng.uniform(25, 70))
            rain = float(rng.exponential(1.8))
            solar = float(rng.uniform(300, 850))
            moisture = float(rng.uniform(0.08, 0.4))
            population = int(rng.uniform(500, 22000))
            elderly = float(rng.uniform(0.04, 0.18))
            suhii = float(
                1.1
                + 4.8 * built
                - 3.2 * ndvi
                - 1.3 * ndwi
                + 1.7 * ndbi
                + 0.075 * (air - 32)
                + 0.001 * solar
                + 0.5 * ndbai
                - 0.8 * moisture
                + rng.normal(0, 0.32)
            )
            props = {
                "id": f"{city.lower()}-{y:02}-{x:02}",
                "name": f"Sector {y+1:02} · {x+1:02}",
                "city": city,
                "spatial_block": x // 3,
                "row": y,
                "column": x,
                "area_km2": 1.0,
                "ndvi": ndvi,
                "ndwi": ndwi,
                "ndbi": ndbi,
                "ndbai": ndbai,
                "building_density": built,
                "population_density": population,
                "population": population,
                "air_temperature": air,
                "humidity": humidity,
                "rainfall": rain,
                "solar_radiation": solar,
                "soil_moisture": moisture,
                "land_cover": int(built > 0.55),
                "observed_suhii": suhii,
                "lst": suhii + rural_reference,
                "rural_reference": rural_reference,
                "elderly_share": elderly,
                "available_land_pct": float(max(0, 100 * (1 - built - ndvi * 0.2))),
                "roof_pct": built * 65,
                "road_pct": built * 25,
                "protected": bool(rng.random() < 0.08),
                "source": "synthetic",
                "acquired_at": "2025-05-15",
                "socioeconomic_data": None,
            }
            zones.append(
                {"type": "Feature", "geometry": mapping(polygon), "properties": props}
            )
    return {
        "type": "FeatureCollection",
        "features": zones,
        "metadata": {
            "source": "Seeded synthetic demonstration dataset",
            "synthetic": True,
            "city": city,
            "center": [lat, lon],
            "resolution_m": 1000,
            "crs": "EPSG:4326",
            "acquisition_date": "2025-05-15",
            "rural_reference_c": rural_reference,
            "rural_method": "Configurable synthetic rural LST; no observed rural reference available.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "limitations": [
                "Synthetic environmental and demographic values; not satellite observations.",
                "Metrics measure recovery of a synthetic relationship, not real-world accuracy.",
                "Vulnerability uses synthetic elderly share; socioeconomic indicators unavailable.",
            ],
        },
    }


def persist_dataset(data):
    import json

    with Session(engine) as s:
        for feature in data["features"]:
            p = feature["properties"]
            row = s.get(Zone, p["id"])
            boundary = (
                f'SRID=4326;{shape(feature["geometry"]).wkt}'
                if POSTGIS
                else json.dumps(feature["geometry"])
            )
            if row:
                row.properties = p
                row.boundary = boundary
            else:
                s.add(Zone(id=p["id"], city=p["city"], properties=p, boundary=boundary))
        s.commit()
    save("dataset", data, record_id=f'dataset-{data["metadata"]["city"]}')
    return data


def normalized_difference(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return np.divide(
        a - b,
        a + b,
        out=np.full(np.broadcast_shapes(a.shape, b.shape), np.nan),
        where=np.abs(a + b) > 1e-10,
    )


def spectral_indices(red, nir, green, swir, thermal=None):
    result = {
        "ndvi": normalized_difference(nir, red),
        "ndwi": normalized_difference(green, nir),
        "ndbi": normalized_difference(swir, nir),
    }
    # NDBaI (Zhao & Chen style) is only meaningful after radiometric normalization.
    if thermal is not None:
        result["ndbai"] = normalized_difference(swir, thermal)
    return result


def landsat_lst(st_b10, qa_pixel):
    values = np.asarray(st_b10) * 0.00341802 + 149.0 - 273.15
    qa = np.asarray(qa_pixel, dtype=np.uint16)
    return np.where((qa & 63) == 0, values, np.nan)
