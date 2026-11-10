import os, sys, tempfile

_temp = tempfile.TemporaryDirectory(prefix="heatwise-diag-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_temp.name, "tests.db")
os.environ["MODEL_DIR"] = os.path.join(_temp.name, "models")
os.environ["MPLCONFIGDIR"] = os.path.join(_temp.name, "mpl")
os.environ["API_TOKEN"] = ""
sys.path.insert(0, "backend")

import app.main as main
from fastapi.testclient import TestClient

print("Pre-populating mock state for Ahmedabad...", flush=True)
main.STATE["Ahmedabad"] = {
    "data": {
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]},
                "properties": {
                    "id": "zone-1",
                    "name": "Zone 1",
                    "predicted_suhii": 3.5,
                    "predicted_lst": 38.5,
                    "rural_reference": 35.0,
                    "interval_low": 2.5,
                    "interval_high": 4.5,
                    "hotspot": False,
                    "risk_score": 0.6,
                    "risk_level": "Medium",
                    "hazard": 0.5,
                    "exposure": 0.7,
                    "vulnerability": 0.6,
                    "population": 15000,
                    "area_km2": 2.5,
                    "available_land_pct": 20.0,
                    "roof_pct": 30.0,
                    "road_pct": 15.0,
                    "protected": False,
                    "water_cost_ratio": 1.0,
                    "shap": {"ndvi": -0.5, "ndbi": 0.8},
                    "shap_base": 2.0
                }
            }
        ],
        "metadata": {"city": "Ahmedabad", "limitations": ["Demonstration only"]}
    },
    "model": {
        "winner": "Random Forest",
        "interval": 0.5,
        "evaluations": [{"model": "Random Forest", "test": {"r2": 0.85, "rmse": 0.4, "mae": 0.3}}],
        "split": {"method": "Spatial Block K-Fold"},
        "metadata": {"city": "Ahmedabad", "limitations": ["Demonstration only"]}
    },
    "importance": [{"feature": "ndbi", "importance": 0.8}, {"feature": "ndvi", "importance": 0.5}]
}

print("Creating TestClient...", flush=True)
client = TestClient(main.app)
print("Sending GET /api/health...", flush=True)
r = client.get("/api/health")
print("Health response:", r.status_code, r.json(), flush=True)

print("Sending GET /api/overview...", flush=True)
r2 = client.get("/api/overview")
print("Overview response:", r2.status_code, r2.json()["city"], flush=True)

print("Sending GET /api/cities...", flush=True)
r3 = client.get("/api/cities")
print("Cities count:", len(r3.json()), flush=True)

print("ALL TESTS PASSED!", flush=True)
