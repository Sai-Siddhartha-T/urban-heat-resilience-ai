import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from app.services.data import sample_data, normalized_difference, landsat_lst


def test_health():
    with TestClient(app) as c:
        assert c.get("/api/health").status_code == 200


def test_synthetic_provenance_and_geometry():
    d = sample_data()
    assert len(d["features"]) == 324 and d["metadata"]["synthetic"]
    p = d["features"][0]["properties"]
    assert (
        p["lst"] - p["rural_reference"] == p["observed_suhii"]
        or abs(p["lst"] - p["rural_reference"] - p["observed_suhii"]) < 1e-10
    )


def test_indices_and_cloud_mask():
    assert np.isclose(normalized_difference(0.8, 0.2), 0.6)
    assert np.isnan(normalized_difference(0, 0))
    assert np.isnan(landsat_lst([44000], [8])[0])
    assert np.isfinite(landsat_lst([44000], [0])[0])
