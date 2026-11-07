import numpy as np
import pytest
from app.db import init_db
from app.services.data import sample_data
from app.services.ml import train, infer
from app.services.planning import risk, simulate, optimize


@pytest.fixture(scope="module")
def analysis():
    init_db()
    d = sample_data()
    a = train(d)
    d, i = infer(d, a)
    for f in d["features"]:
        f["properties"].update(risk(f["properties"]))
    return d, a, i


def test_models_spatial_evaluation(analysis):
    d, a, i = analysis
    assert len(a["evaluations"]) == 3
    assert a["split"] == {
        "training": 162,
        "validation": 54,
        "test": 54,
        "buffer": 54,
        "method": a["split"]["method"],
    }
    for m in a["evaluations"]:
        assert np.isfinite(m["test"]["rmse"]) and m["test"]["rmse"] > 0
    assert "lst" not in a["features"] and "observed_suhii" not in a["features"]


def test_shap_additivity(analysis):
    for f in analysis[0]["features"]:
        p = f["properties"]
        assert (
            abs(p["shap_base"] + sum(p["shap"].values()) - p["predicted_suhii"]) < 1e-4
        )


def test_simulation_constraints(analysis):
    p = analysis[0]["features"][0]["properties"]
    assert not simulate(p, {"trees": 100})["feasible"]
    assert not simulate(p, {"cool_roofs": 5, "roof_gardens": 5})["feasible"]
    assert not simulate(p, {"water": 5}, 0)["feasible"]
    assert not simulate({**p, "protected": True}, {"trees": 5})["feasible"]
    assert simulate(p, {}, 0)["estimated_cooling"] == 0
    with pytest.raises(ValueError):
        simulate(p, {"fake": 3})


def test_optimizer_constraints_and_infeasibility(analysis):
    zones = [f["properties"] for f in analysis[0]["features"][:5]]
    r = optimize(zones, 300, 20)
    assert r["feasible"] and r["water_used"] <= 300
    for s in r["selections"]:
        assert s["feasible"] and not s["violations"]
    impossible = optimize(zones, 0, 0, 4, 0)
    assert not impossible["feasible"] and impossible["status"] == "INFEASIBLE"


def test_risk_is_not_population_only(analysis):
    p = analysis[0]["features"][0]["properties"]
    assert (
        risk({**p, "elderly_share": 0.2})["risk_score"]
        > risk({**p, "elderly_share": 0.05})["risk_score"]
    )
