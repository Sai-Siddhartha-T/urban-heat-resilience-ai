# Heatwise evidence API, version 1

These additive endpoints support normal operation without synthetic zones or a trained model. Existing analytical routes remain available separately. The source of truth is `backend/app/schemas/evidence.py`.

## Routes

* `GET /api/workspace?city=Ahmedabad`: a normal-mode workspace; never triggers training, demo creation or external retrieval.
* `GET /api/data/assets?city=Ahmedabad&category=weather`: summary list, latest first. `category` is optional. Demo and unscoped legacy records are excluded.
* `GET /api/data/assets/{id}?city=Ahmedabad`: one summary plus `payload`; another city's ID returns 404. A city is required.
* `GET /api/data/layers?city=Ahmedabad`: `{city,layers}`; every supported layer is listed, including unavailable layers.
* Existing `POST /api/data/ingest`: retrieves and persists evidence, then invalidates the client's workspace/assets/layers queries. Normal evidence never activates a model automatically.

Supported city values are exactly `Ahmedabad`, `Delhi`, and `Hyderabad`. Coordinates in GeoJSON are longitude, latitude in WGS84. `center` is latitude, longitude for Leaflet. Dates are source dates or ISO 8601 timestamps; source timestamps are never replaced by retrieval time.

## Workspace

```json
{
  "schema_version": "1",
  "city": "Ahmedabad",
  "center": [23.0225, 72.5714],
  "mode": "normal",
  "analysis": {"status":"unavailable","reason":"No verified surface-temperature observations are available.","synthetic":false,"dataset_id":null},
  "assets": [],
  "layers": [],
  "capabilities": {},
  "limitations": []
}
```

`analysis.available` means verified observed surface-temperature evidence is present. It does **not** mean an ML model is trained or validated. Consult `capabilities.prediction` and `capabilities.explainability` separately. Capability values are `{status:'available'|'partial'|'unavailable',reason:string|null,asset_ids:string[]}`. A weather-only workspace is useful and returns HTTP 200.

## Evidence asset

Every summary has `id`, `city`, `category`, `source`, `mode` (`live` or `demo`), `analysis_ready`, `provenance`, `created_at`. The detail adds `payload`, the adapter's actual returned data. Canonical categories: `weather`, `air_quality`, `groundwater`, `satellite`, `population`, `land_cover`, `elevation`, `infrastructure`. Catalog discovery is evidence of catalog availability, not of measured population or processed surface heat.

Provenance fields:

```text
source: string
category: string
mode: live | demo
kind: observed | modelled | forecast | predicted | hypothetical
status: string (e.g. latest_available, historical, forecast, unavailable)
retrieved_at: ISO timestamp
observation_time: source timestamp/date | array of source timestamps/dates | null
city: string | null
coverage: string | null
resolution: string | null
units: record(variable -> unit)
processing: string | null
quality: string | null
freshness: current | latest_available | historical | stale | unknown
analysis_ready: boolean
limitations: string[]
```

Adapters should return explicit `source`, `synthetic:false`, source observation dates and units. They may include a `provenance` object with the fields above. Unknown metadata stays null/unknown. Adapters may return `layers` as described below. Future adapters should acquire data without independently persisting it; the route owns the acquisition transaction.

Existing weather payload is `{source,synthetic:false,latitude,longitude,resolution,data:<Open-Meteo response>}`. Its `data.current`, `data.current_units`, `data.hourly`, `data.hourly_units`, `data.daily`, and `data.daily_units` retain provider field names and timestamps. Current Open-Meteo weather is modelled; hourly/daily future values are forecasts. New station adapters should return `stations` with actual `id`, `name`, `latitude`, `longitude`, `measurements` (variable/value/unit/observation_time), `distance_m` when computed, and source/quality/limitations. Groundwater values require observation dates and `depth_below_ground_m`; no soil-moisture conversion.

## Map layers

Fixed IDs: `lst`, `predicted_lst`, `suhii`, `ndvi`, `building_density`, `land_cover`, `air_quality`, `weather`, `groundwater`, `heat_risk`, `population`, `interventions`. Additional evidence variables such as `ndwi`, `ndbi`, or `elevation` may be included.

```text
id, name, variable: string
status: available | unavailable
kind: observed | modelled | forecast | predicted | hypothetical
source, retrieved_at, resolution, unit, asset_id, reason: string | null
observation_time: string | string[] | null
geojson: GeoJSON FeatureCollection | null
raster: RasterGrid | null
limitations: string[]
```

An available layer must contain genuine georeferenced observations/estimates. Missing layers have null geometry and an actionable `reason`. `geojson.features[].properties.value` is the selected numeric value (null for missing); retain original station/zone properties for selection. Feature dates and units override layer-wide metadata when observations differ. Do not manufacture polygons for station coverage or empty maps.

`RasterGrid` is `{crs:string,transform:[a,b,c,d,e,f],shape:[height,width],values:(number|null)[][],bounds:[west,south,east,north]|null}`. Affine order follows Rasterio: `x=a*col+b*row+c`, `y=d*col+e*row+f`. Values and the affine refer to the **actual processed raster**, never an illustrative grid. Bounds, when supplied, are WGS84. Display code must respect CRS and rotated affine transforms. Pixel nulls are no-data, not zero. Native resolution and processing limitations must remain in metadata when a display grid is aggregated.

## Failure and demo behavior

Unavailability of one source does not turn the workspace into a 409 or create invented data. Invalid cities/requests return 422; unavailable asset IDs return 404. Source request failures return a useful upstream error and leave existing evidence intact. Source credentials configured, authentication successful, latest retrieval successful and last success time are distinct statuses.

Normal workspace/assets/layers always exclude demo evidence, even if a demo is activated elsewhere. Legacy analysis accepts explicit `mode=demo` for GET or `mode:'demo'` in request JSON; a development `HEATWISE_DEMO_MODE=1` flag remains supported for existing demo tests. Cache entries for normal and demo analysis are separate. No demographic values, heat values, metrics, SHAP, or intervention cooling are filled to satisfy these contracts.
