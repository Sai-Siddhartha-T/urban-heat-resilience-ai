# Demographic Data Ingestion & Vulnerability Assessment

This document describes the demographic data ingestion pipeline, multidimensional vulnerability calculations, and parametric heat risk integration within the Urban Heat Resilience AI platform.

---

## 1. Overview & Objectives

Accurate urban heat vulnerability analysis requires moving beyond simple aggregate population counts. The demographic ingestion service (`backend/app/services/demographics.py`) retrieves real demographic data from global and local providers, computes age structures and vulnerability indicators, stores comprehensive provenance metadata, and provides deterministic synthetic fallbacks when external APIs are unreachable or offline.

The risk service (`backend/app/services/risk.py`) incorporates these demographic indicators to evaluate heat hazard, human exposure, and multidimensional vulnerability according to the IPCC AR5/AR6 framework.

---

## 2. Architecture & Modules

```
backend/
├── app/
│   ├── services/
│   │   ├── demographics.py     # WorldPop, GHSL, Census ingestion & indicator calculation
│   │   ├── risk.py             # Parametric IPCC AR5/AR6 risk and multidimensional vulnerability
│   │   └── planning.py         # Interventions simulation & solver (imports risk service)
│   └── routes/
│       └── risk.py             # FastAPI router exposing /api/risk/analyze
└── tests/
    └── test_demographics.py    # Unit tests with HTTP/STAC mocks, fallbacks, and risk integration
```

---

## 3. Supported Data Sources

| Source | Protocol / Format | Typical Resolution | Extracted Attributes |
|---|---|---|---|
| **WorldPop** | HTTP REST (`/rest/data/pop/wpgp`) | 100m grid | Population counts, dasymetric density, age-sex structures |
| **GHSL** | STAC API (Humanitarian Data Cube) | 100m / 1km grid | GHS-POP residential tiles, built-up surfaces |
| **Census** | HTTP Tabular (`/data/{year}/dec/dhc`) | Ward / Tract level | Census enumeration, poverty rate, informal housing, cooling access |
| **Synthetic Fallback** | Local Deterministic Model | 1000m grid | Full synthetic profile with explicit fallback labels and caveats |

### 3.1 Standardized Schema
Every demographic ingestion adapter returns a consistent, standardized schema:
- `source`: Identifier string (`"WorldPop"`, `"GHSL"`, `"Census"`, or `"synthetic"`).
- `synthetic`: Boolean indicating whether values are synthetic estimates.
- `fallback`: Boolean indicating whether a fallback path was taken.
- `city`: Target metropolitan city name.
- `latitude`, `longitude`: Zone or centroid geographic coordinates.
- `area_km2`: Bounding or administrative area in km².
- `total_population`: Total headcount.
- `population_density`: Population per km².
- `age_groups`: Normalized dictionary containing `children_share`, `working_age_share`, `elderly_share`, `dependency_ratio`, and `aging_index`.
- `socioeconomic_indicators`: Dictionary or `None` containing `poverty_rate`, `informal_housing_pct`, `outdoor_worker_share`, `cooling_access_pct`.
- `vulnerability_indicators`: Multidimensional sensitivity, deprivation, cooling deficit, and composite vulnerability index.
- `metadata`: Comprehensive provenance, acquisition date, resolution, CRS, and limitations.

---

## 4. Key Indicators & Mathematical Formulations

### 4.1 Population Density
$$
\text{Density} = \frac{\text{Total Population}}{\text{Area (km}^2\text{)}}
$$
Edge cases (e.g. non-positive area, NaN, non-finite values, numeric strings, nulls) are safely bounded to `0.0`.

### 4.2 Age Distribution & Demographic Ratios
- **Children Share** ($c$): Ages 0–14 as proportion of total population.
- **Working-Age Share** ($w$): Ages 15–64 as proportion of total population.
- **Elderly Share** ($e$): Ages 65+ as proportion of total population (highest physiological heat sensitivity).
- **Dependency Ratio**:
  $$
  \text{Dependency Ratio} = \frac{c + e}{\max(w, 10^{-4})}
  $$
- **Aging Index**:
  $$
  \text{Aging Index} = \frac{e}{\max(c, 10^{-4})} \times 100
  $$

When component counts are provided without a known total, total population is derived directly from the sum of the components.

### 4.3 Multidimensional Vulnerability Pillars
Vulnerability combines three distinct dimensions:
1. **Demographic Sensitivity** ($S_{\text{demo}}$):
   $$
   S_{\text{demo}} = \min\left(1.0, 0.65 \times \frac{e}{0.25} + 0.35 \times \frac{c}{0.30}\right)
   $$
2. **Socioeconomic Deprivation** ($S_{\text{socio}}$):
   Arithmetic mean of normalized poverty rate, informal housing share, and outdoor worker proportion.
3. **Adaptive Capacity Deficit** ($D_{\text{cooling}}$):
   Deficit in cooling infrastructure and air conditioning access:
   $$
   D_{\text{cooling}} = 1.0 - \text{Cooling Access Proportion}
   $$

### 4.4 Parametric Heat Risk Score
In `backend/app/services/risk.py`, parametric risk is evaluated using:
$$
\text{Risk Score} = 100 \times \text{Hazard}^{w_H} \times \text{Exposure}^{w_E} \times \text{Vulnerability}^{w_V}
$$
Where:
- $\text{Hazard} = \min(1.0, \max(0.0, \text{SUHII}) / 8.0)$
- $\text{Exposure} = \min(1.0, \text{Population Density} / 25,000)$
- $\text{Vulnerability} = \min(1.0, S_{\text{demo}} + 0.25 \times S_{\text{socio}} + 0.25 \times D_{\text{cooling}})$
- Categorical levels:
  - **High**: $\text{Risk Score} \ge 20$
  - **Moderate**: $8 \le \text{Risk Score} < 20$
  - **Low**: $\text{Risk Score} < 8$

The risk service automatically extracts demographic variables whether supplied at the zone top-level or nested inside a zone `demographics` object.

---

## 5. Metadata Schema & Provenance

Every ingestion result generates a standardized metadata object:
```json
{
  "source": "WorldPop Global High Resolution Population Denominators",
  "source_type": "WorldPop",
  "acquisition_date": "2020",
  "date": "2020",
  "resolution_m": 100,
  "resolution": "100m",
  "crs": "EPSG:4326",
  "synthetic": false,
  "fallback": false,
  "limitations": [
    "Gridded population model using random forest dasymetric mapping.",
    "Sub-national age structures derived from national census surveys."
  ]
}
```

---

## 6. Synthetic Fallback Labeling

When remote endpoints are unavailable, offline, or rate-limited, the system automatically falls back to synthetic demographic estimates. Every synthetic response includes explicit provenance indicators:
```json
{
  "source": "synthetic",
  "synthetic": true,
  "fallback": true,
  "fallback_reason": "Fetch failed for auto: Connection timed out",
  "metadata": {
    "source": "synthetic",
    "synthetic": true,
    "fallback": true,
    "resolution_m": 1000,
    "limitations": [
      "Synthetic demonstration demographic estimates; not official census counts.",
      "Age group distribution and socioeconomic variables are modeled proxies.",
      "Not for direct operational or municipal emergency deployment."
    ]
  }
}
```

---

## 7. Python Usage Examples

### 7.1 Ingest Demographics
```python
import asyncio
from app.services import demographics

# Ingest via auto-detection (WorldPop -> GHSL -> Census -> Synthetic Fallback)
data = asyncio.run(demographics.ingest_demographics(
    source="auto",
    city="Ahmedabad",
    lat=23.0225,
    lon=72.5714,
    year=2020,
    area_km2=1.0,
))

print(f"Source: {data['source']} (Synthetic: {data['synthetic']})")
print(f"Population Density: {data['population_density']} people/km²")
print(f"Elderly Share: {data['elderly_share']}, Children Share: {data['children_share']}")
```

### 7.2 Calculate Parametric Risk with Enhanced Demographics
```python
from app.services import risk

zone_properties = {
    "predicted_suhii": 3.8,
    "population_density": 18500,
    "elderly_share": 0.16,
    "children_share": 0.28,
    "poverty_rate": 0.32,
    "cooling_deficit": 0.65,
}

result = risk.risk(zone_properties, weights=(1.0, 1.0, 1.0))
print(f"Risk Score: {result['risk_score']:.2f} ({result['risk_level']})")
print(f"Missing Indicators: {result['missing_indicators']}")
```

### 7.3 Zone with Nested Demographic Payload
```python
from app.services import risk

zone_with_nested = {
    "predicted_suhii": 3.5,
    "demographics": {
        "source": "WorldPop",
        "synthetic": False,
        "population_density": 16000.0,
        "elderly_share": 0.15,
        "children_share": 0.25,
    }
}

result = risk.risk(zone_with_nested)
print(f"Exposure: {result['exposure']}")  # 16000 / 25000 = 0.64
print(f"Vulnerability: {result['vulnerability']}")  # Derived from demographic age shares
print(f"Synthetic: {result['synthetic_demographics']}")  # False
```

---

## 8. Unit Testing

Unit tests are implemented under `backend/tests/test_demographics.py`. All external HTTP and STAC network requests are mocked using `monkeypatch` to ensure fast, isolated, and deterministic test runs.

To run the demographic unit test suite:
```bash
python -m pytest backend/tests/test_demographics.py
```
Coverage includes:
- Density calculations and boundary conditions (zero/negative area, null values, numeric strings, non-finite floats).
- Age distributions, dependency ratios, zero total population component sums, and aging index computations.
- Multidimensional vulnerability index, embedded socioeconomic indicators, and risk categorization.
- WorldPop, GHSL, and Census mocked responses, multi-row matching, error handling, and fallbacks.
- Nested demographic object extraction and missing indicators tracking in `risk.py`.
- None-safety and NaN-safety across parametric risk assessment components.
