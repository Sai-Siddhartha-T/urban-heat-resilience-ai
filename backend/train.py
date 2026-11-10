"""Standalone spatial training, with synthetic or supplied labeled GeoJSON data."""

import argparse, json
import numpy as np
from pyproj import Transformer
from shapely.geometry import shape
from app.db import init_db
from app.services.data import sample_data, persist_dataset, CITIES, FEATURES
from app.services.ml import train, describe

parser = argparse.ArgumentParser(
    description="Train spatially separated RF/XGBoost/LightGBM models; report provenance explicitly."
)
parser.add_argument("--city", choices=list(CITIES), default="Ahmedabad")
parser.add_argument(
    "--input",
    help="Optional preprocessed, labeled GeoJSON FeatureCollection. Does not replace dashboard sample data.",
)
parser.add_argument(
    "--folds",
    type=int,
    default=None,
    help="Optional number of KMeans spatial cross-validation folds (minimum 3).",
)
args = parser.parse_args()
init_db()
if args.input:
    with open(args.input) as f:
        data = json.load(f)
    if data.get("type") != "FeatureCollection" or len(data.get("features", [])) < 180:
        raise ValueError("Provide at least 180 labeled spatial cells.")
    metadata = data.get("metadata", {})
    if not all(
        k in metadata
        for k in ["source", "synthetic", "acquisition_date", "rural_method", "crs"]
    ):
        raise ValueError(
            "Provide source, synthetic flag, acquisition_date, rural_method, and crs metadata."
        )
    if metadata["crs"] != "EPSG:4326":
        raise ValueError(
            "Input GeoJSON geometry must be WGS84. Align source features before export."
        )
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)
    centers = []
    for feature in data["features"]:
        geom = shape(feature["geometry"])
        p = feature["properties"]
        if not geom.is_valid or geom.is_empty:
            raise ValueError("Invalid geometry.")
        if any(k not in p for k in FEATURES):
            raise ValueError(
                "Every cell must supply all documented feature keys; use null for missing inputs."
            )
        if not all(
            isinstance(p.get(k), (int, float)) and np.isfinite(p[k])
            for k in ["lst", "rural_reference"]
        ):
            raise ValueError(
                "Each cell requires measured LST and matched rural reference LST in Celsius."
            )
        p["observed_suhii"] = p["lst"] - p["rural_reference"]
        centers.append(transformer.transform(geom.centroid.x, geom.centroid.y)[0])
    span = max(centers) - min(centers)
    if span <= 0:
        raise ValueError("Dataset needs east-west spatial extent.")
    for f, x in zip(data["features"], centers):
        f["properties"]["spatial_block"] = min(5, int((x - min(centers)) / span * 6))
    from datetime import datetime, timezone

    # Separate model namespace keeps observed training artifacts out of the demonstration dashboard.
    metadata.update(
        city=args.city + "-external",
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
else:
    data = persist_dataset(sample_data(args.city))
artifact = train(data, n_folds=args.folds)
print(json.dumps(describe(artifact), indent=2))
