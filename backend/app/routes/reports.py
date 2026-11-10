"""Municipal report generation and multi-format export (JSON, CSV, Markdown)."""

import csv
import io
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from app.db import save, records
from app.schemas import ZoneRequest
from app.services.planning import ASSUMPTIONS
from app.services.state import state, get_city_overview

router = APIRouter(prefix="/api/reports", tags=["reports"])


def find_report(identifier: str) -> dict:
    """Retrieve persisted report record by ID or raise HTTP 404."""
    row = next((r for r in records("report", 1000) if r.get("id") == identifier), None)
    if not row:
        raise HTTPException(404, "Report not found.")
    return row


@router.post("/generate")
def generate_report(req: ZoneRequest):
    """Generate comprehensive synthesis report across models, zones, scenarios, and optimizations."""
    s = state(req.city, req.mode)
    summary = get_city_overview(req.city, req.mode)
    scens = [r for r in records("scenario") if r.get("city") == req.city]
    opts = [r for r in records("optimization") if r.get("city") == req.city]
    content = {
        "title": f"{req.city} · Urban Heat Analysis",
        "summary": summary,
        "metadata": s["data"]["metadata"],
        "models": s["model"],
        "zones": [f["properties"] for f in s["data"]["features"]],
        "scenarios": scens,
        "optimization": opts[:1],
        "limitations": s["data"]["metadata"]["limitations"] + ASSUMPTIONS,
    }
    identifier = save("report", content)
    return {
        "id": identifier,
        "download_url": f"/api/reports/{identifier}/download",
        "csv_url": f"/api/reports/{identifier}/csv",
        "markdown_url": f"/api/reports/{identifier}/markdown",
    }


@router.get("/{identifier}/download")
def download_report(identifier: str):
    """Download full report document in JSON format."""
    return Response(
        json.dumps(find_report(identifier), indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="heatwise-report.json"'},
    )


@router.get("/{identifier}/csv")
def csv_report(identifier: str):
    """Export tabular zone metrics and predictions as CSV."""
    row = find_report(identifier)
    output = io.StringIO()
    keys = [
        "id",
        "name",
        "predicted_suhii",
        "predicted_lst",
        "interval_low",
        "interval_high",
        "risk_score",
        "population",
        "partition",
        "source",
    ]
    writer = csv.DictWriter(output, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(row["zones"])
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="heatwise-zones.csv"'},
    )


@router.get("/{identifier}/markdown")
def markdown_report(identifier: str):
    """Export executive briefing summary in GitHub-flavored Markdown."""
    r = find_report(identifier)
    s = r["summary"]
    lines = [
        f'# {r["title"]}',
        "",
        "**SYNTHETIC DEMONSTRATION — not validated planning evidence.**",
        "",
        f'Area: {s["area_km2"]:.0f} km². Mean predicted SUHII: {s["average_suhii"]:.2f}°C. Hotspots: {s["hotspots"]}.',
        "",
        "## Held-out synthetic evaluation",
        "Model | R² | RMSE °C | MAE °C",
        "--- | --- | --- | ---",
    ]
    lines += [
        f'{m["model"]} | {m["test"]["r2"]:.3f} | {m["test"]["rmse"]:.3f} | {m["test"]["mae"]:.3f}'
        for m in r["models"]["evaluations"]
    ]
    lines += ["", "## Method and limitations", r["models"]["split"]["method"]] + [
        "- " + l for l in r["limitations"]
    ]
    lines += [
        "",
        "## Scenarios",
        json.dumps(r["scenarios"], indent=2),
        "## Optimization",
        json.dumps(r["optimization"], indent=2),
    ]
    return Response(
        "\n".join(lines),
        media_type="text/markdown",
        headers={"Content-Disposition": 'attachment; filename="heatwise-report.md"'},
    )
