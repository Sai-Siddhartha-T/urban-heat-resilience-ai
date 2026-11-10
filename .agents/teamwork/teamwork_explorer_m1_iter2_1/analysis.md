# Analysis Report: Routing & State Synchronization Architecture

**Agent:** Explorer M1-Iter2-1 (Routing & State Synchronization Specialist)  
**Date:** 2026-11-08  
**Scope:** Milestone 1 Iteration 2 — Frontend State & Route Synchronization  
**Target Files:**  
- `frontend/src/App.tsx`
- `frontend/src/pages/ZoneComparePage.tsx`
- `frontend/src/lib/constants.ts`
- `frontend/src/hooks/useHashRouter.ts`
- `frontend/src/tests/integration_challenge.test.ts`

---

## 1. Executive Summary

Milestone 1 established a modular React frontend structure (<150-line `App.tsx`, multi-page routing, rich comparison and time-series charts). However, Gate Iteration 1 was blocked by two primary state synchronization defects identified by Reviewer M1-2 and Challenger M1-2:
1. **Hash Router & React State Desynchronization (`App.tsx`):** `route.zoneId` is discarded from `useHashRouter()`. Direct deep-links with `?zone=...` and inter-page action triggers from `ZoneComparePage` (`navigate("Intervention simulator", { zone: z.id })`) fail to update `selectedZone`, leaving target pages displaying the default first zone instead of the requested zone.
2. **City Switch Ghost Zones (`ZoneComparePage.tsx`):** `selectedIds` is initialized only once upon component mounting (`useState(defaultSelected)`). When the user switches cities in `Topbar`, the GeoJSON features update to the new city, but `selectedIds` retains IDs from the prior city (`["AHM_01", "AHM_02"]`). As a result, `selectedZones` filters to empty `[]`, disabling comparison cards/charts and blocking user interactions once 4 stale IDs accumulate.
3. **Missing Plural Route Slugs (`constants.ts`):** Common URLs such as `/#/predictions` or `/#/simulations` fail `PAGE_MAP` lookup and erroneously fall back to the overview page.

This report provides the exact root-cause breakdown and complete drop-in replacement code for Worker M1-Iter2.

---

## 2. Root Cause Analysis

### 2.1 Issue 1: `App.tsx` Route Desynchronization

#### Observed Code (`frontend/src/App.tsx:19, 34-41`):
```typescript
19: const { page, city, layer, navigate, setCity, setLayer } = useHashRouter();
...
34: useEffect(() => {
35:   if (data.data?.features?.length) {
36:     const match = data.data.features.find((f: ZoneFeature) => f.properties.id === selectedZone?.id);
37:     setSelectedZone(match ? match.properties : data.data.features[0].properties);
38:   }
39: }, [data.data, city]);
41: const activeZone = selectedZone || data.data?.features?.[0]?.properties;
```

#### Defect Breakdown:
1. **Discarded Parameter:** `useHashRouter` parses `?zone=` from the URL hash into `route.zoneId`, but `App.tsx` line 19 does not destructure `zoneId`.
2. **Missing Dependency in Effect:** `useEffect` only listens to `[data.data, city]`. When the user clicks an action button in `ZoneComparePage` (`navigate("Intervention simulator", { zone: z.id })`), `city` and `data.data` do not change. Therefore, the `useEffect` never executes.
3. **No Target ID Resolution:** Line 36 only searches for `selectedZone?.id`. On deep-link or page transition, `selectedZone` is either stale or `null`, completely ignoring the incoming route `zoneId`.
4. **Stale Active Zone Fallback:** Line 41 falls back to `data.data.features[0].properties` only if `selectedZone` is falsy. If `city` changes, `selectedZone` momentarily holds an object from the previous city, which can cause UI components to render mismatched city data before the effect fires.

---

### 2.2 Issue 2: `ZoneComparePage.tsx` City State Desynchronization

#### Observed Code (`frontend/src/pages/ZoneComparePage.tsx:24-46`):
```typescript
24: export function ZoneComparePage({
25:   data,
26:   navigate,
27: }: ZoneComparePageProps) {
28:   const allZones: ZoneProperties[] = data?.features?.map((f: ZoneFeature) => f.properties) || [];
29: 
30:   // Default to the first two zones (or top 2 hotspots)
31:   const defaultSelected = allZones.slice(0, 2).map((z) => z.id);
32:   const [selectedIds, setSelectedIds] = useState<string[]>(defaultSelected);
33: 
34:   const selectedZones = allZones.filter((z) => selectedIds.includes(z.id));
```

#### Defect Breakdown:
1. **Missing Props Destructuring:** Props interface `ZoneComparePageProps` specifies `city`, `selected`, `onSelect`, and `notify`, but lines 24–27 only destructure `data` and `navigate`.
2. **Mount-Only State Initialization:** `useState(defaultSelected)` initializes `selectedIds` during the initial mount. When `city` changes, `data` changes, but React preserves state for the mounted component instance.
3. **Ghost Zone IDs:** In Ahmedabad, `selectedIds` is `["AHM_01", "AHM_02"]`. After switching to Delhi, `allZones` has IDs `["DEL_01", "DEL_02", ...]`. `selectedZones = allZones.filter(z => selectedIds.includes(z.id))` returns `[]`.
4. **Lockout upon 4 Selections:** If a user clicks chips to add Delhi zones, the array becomes `["AHM_01", "AHM_02", "DEL_01", "DEL_02"]`. `toggleZone` rejects further additions because `selectedIds.length < 4` is false, locking the user to only 2 visible zones.
5. **Disconnected Navigation Action Buttons:** In lines 274 and 281:
   ```typescript
   onClick={() => navigate("Intervention simulator", { zone: z.id })}
   ```
   `onSelect` is not invoked, relying solely on hash router navigation which was broken in `App.tsx`.

---

### 2.3 Issue 3: `constants.ts` Missing Plural & Title Slugs in `PAGE_MAP`

#### Observed Code (`frontend/src/lib/constants.ts:54-83`):
```typescript
export const PAGE_MAP: Record<string, PageDefinition> = {
  overview: PAGES[0],
  Overview: PAGES[0],
  map: PAGES[1],
  "Heat map": PAGES[1],
  Map: PAGES[1],
  compare: PAGES[2],
  "Zone comparison": PAGES[2],
  ZoneCompare: PAGES[2],
  prediction: PAGES[3],
  "AI prediction": PAGES[3],
  Prediction: PAGES[3],
  ...
};
```

#### Defect Breakdown:
1. `PAGE_MAP` only contains singular slugs (`prediction`, `simulator`).
2. URLs frequently reference plural forms (`/#/predictions`, `/#/simulations`, `/#/risks`, `/#/comparisons`, `/#/reports`).
3. When `/#/predictions` is loaded, `PAGE_MAP["predictions"]` evaluates to `undefined`, and `useHashRouter.ts` line 11 defaults to `PAGE_MAP.overview`. Users are redirected unexpectedly to the Overview page.

---

### 2.4 Issue 4: `useHashRouter.ts` City Switch Zone Bleed

In `frontend/src/hooks/useHashRouter.ts:75-80`:
```typescript
const setCity = useCallback(
  (city: City) => {
    navigate({ city });
  },
  [navigate],
);
```
When `setCity("Delhi")` is called, `navigate({ city })` retains `route.zoneId` from Ahmedabad (e.g. `AHM_03`). The hash becomes `#/simulator?city=Delhi&zone=AHM_03`. While `App.tsx` can fall back to the first Delhi zone, the URL remains dirty with the stale zone ID. Clearing `zoneId: ""` on city change ensures pristine URL hygiene.

---

## 3. Implementation Blueprint for Worker M1-Iter2

### 3.1 Drop-In Replacement for `frontend/src/App.tsx`

```tsx
import React, { useState, useEffect } from "react";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import type { City, ZoneFeature, ZoneProperties } from "./types";
import { heatService, dataService } from "./services";
import { useHashRouter } from "./hooks/useHashRouter";
import { Sidebar, Topbar } from "./components/layout";
import { Pending } from "./components/common/Pending";
import { DataDialog } from "./components/modals/DataDialog";
import {
  OverviewPage, MapPage, PredictionsPage, ExplainPage, RiskPage,
  SimulatorPage, OptimizerPage, AssistantPage, ReportsPage, ZoneComparePage,
} from "./pages";

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } },
});

function HeatwiseApp() {
  const { page, city, zoneId, layer, navigate, setCity, setLayer } = useHashRouter();
  const [showData, setShowData] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);
  const [selectedZone, setSelectedZone] = useState<ZoneProperties | null>(null);

  const notify = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 4000);
  };

  const health = useQuery({ queryKey: ["health"], queryFn: heatService.getHealth });
  const overview = useQuery({ queryKey: ["overview", city], queryFn: () => heatService.getOverview(city) });
  const data = useQuery({ queryKey: ["map", city], queryFn: () => heatService.getHeatMap(city) });
  const status = useQuery({ queryKey: ["status"], queryFn: dataService.getDataStatus });

  // Synchronize selectedZone whenever features load, city changes, or route.zoneId changes
  useEffect(() => {
    if (data.data?.features?.length) {
      const targetId = zoneId || selectedZone?.id;
      const match = data.data.features.find(
        (f: ZoneFeature) => f.properties.id === targetId,
      );
      setSelectedZone(match ? match.properties : data.data.features[0].properties);
    }
  }, [data.data, city, zoneId]);

  // Ensure activeZone always belongs to the currently active city's feature set
  const activeZone =
    (selectedZone && data.data?.features?.some((f: ZoneFeature) => f.properties.id === selectedZone.id))
      ? selectedZone
      : data.data?.features?.[0]?.properties;

  const handleSelectZone = (zone: ZoneProperties) => {
    setSelectedZone(zone);
    if (zone.id !== zoneId) {
      navigate({ zoneId: zone.id });
    }
  };

  return (
    <div className="layout">
      <Sidebar currentPage={page} onNavigate={navigate} city={city} />
      <div className="main">
        <Topbar
          city={city}
          onCityChange={(c: City) => setCity(c)}
          onOpenData={() => setShowData(true)}
          databaseStatus={health.data?.database}
        />
        {notification && <div className="toast-notification">{notification}</div>}

        <main className="content">
          {!overview.data || !data.data || !activeZone ? (
            <Pending message={`Loading spatial intelligence for ${city}…`} />
          ) : (
            <>
              {page === "overview" && <OverviewPage city={city} overview={overview.data} data={data.data} selected={activeZone} onSelect={handleSelectZone} layer={layer} onLayer={setLayer} navigate={navigate} />}
              {page === "map" && <MapPage city={city} data={data.data} overview={overview.data} selected={activeZone} onSelect={handleSelectZone} layer={layer} onLayer={setLayer} navigate={navigate} />}
              {page === "compare" && <ZoneComparePage key={city} city={city} data={data.data} selected={activeZone} onSelect={handleSelectZone} navigate={navigate} notify={notify} />}
              {page === "prediction" && <PredictionsPage city={city} data={data.data} overview={overview.data} notify={notify} onOpenDataDialog={() => setShowData(true)} />}
              {page === "explain" && <ExplainPage city={city} data={data.data} selected={activeZone} onSelect={handleSelectZone} overview={overview.data} />}
              {page === "risk" && <RiskPage city={city} data={data.data} selected={activeZone} onSelect={handleSelectZone} />}
              {page === "simulator" && <SimulatorPage city={city} data={data.data} selected={activeZone} onSelect={handleSelectZone} notify={notify} />}
              {page === "optimizer" && <OptimizerPage city={city} overview={overview.data} notify={notify} />}
              {page === "assistant" && <AssistantPage city={city} data={data.data} selected={activeZone} onSelect={handleSelectZone} navigate={navigate} />}
              {page === "reports" && <ReportsPage city={city} overview={overview.data} status={status.data} notify={notify} />}
            </>
          )}
        </main>
      </div>

      {showData && <DataDialog city={city} close={() => setShowData(false)} notify={notify} />}
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <HeatwiseApp />
    </QueryClientProvider>
  );
}
```

---

### 3.2 Drop-In Replacement for `frontend/src/pages/ZoneComparePage.tsx`

```tsx
import React, { useState, useEffect } from "react";
import {
  Thermometer,
  ArrowRight,
  Check,
  Sparkles,
  Scale,
} from "lucide-react";
import type { City, ZoneFeature, ZoneFeatureCollection, ZoneProperties } from "../types";
import { ZoneComparisonChart } from "../components/charts/ZoneComparisonChart";
import { Button } from "../components/common/Button";
import { Badge } from "../components/common/Badge";
import { fmt } from "../lib/utils";

export interface ZoneComparePageProps {
  city: City | string;
  data: ZoneFeatureCollection | undefined;
  selected?: ZoneProperties;
  onSelect?: (zone: ZoneProperties) => void;
  navigate: (page: string, params?: Record<string, string>) => void;
  notify?: (message: string) => void;
}

export function ZoneComparePage({
  city,
  data,
  onSelect,
  navigate,
}: ZoneComparePageProps) {
  const allZones: ZoneProperties[] = data?.features?.map((f: ZoneFeature) => f.properties) || [];

  // Default to the first two zones (or top 2 hotspots)
  const defaultSelected = allZones.slice(0, 2).map((z) => z.id);
  const [selectedIds, setSelectedIds] = useState<string[]>(defaultSelected);

  // Synchronize or reset selectedIds when city changes or data updates
  useEffect(() => {
    if (allZones.length > 0) {
      const validIds = selectedIds.filter((id) => allZones.some((z) => z.id === id));
      if (validIds.length > 0) {
        if (validIds.length !== selectedIds.length) {
          setSelectedIds(validIds);
        }
      } else {
        setSelectedIds(allZones.slice(0, 2).map((z) => z.id));
      }
    }
  }, [city, data]);

  const selectedZones = allZones.filter((z) => selectedIds.includes(z.id));

  const toggleZone = (id: string) => {
    if (selectedIds.includes(id)) {
      if (selectedIds.length > 1) {
        setSelectedIds(selectedIds.filter((item) => item !== id));
      }
    } else {
      if (selectedIds.length < 4) {
        setSelectedIds([...selectedIds, id]);
      }
    }
  };

  const selectTopHotspots = () => {
    const sorted = [...allZones].sort((a, b) => b.predicted_suhii - a.predicted_suhii);
    setSelectedIds(sorted.slice(0, 3).map((z) => z.id));
  };

  const selectExtremeContrast = () => {
    if (allZones.length < 2) return;
    const sorted = [...allZones].sort((a, b) => b.predicted_suhii - a.predicted_suhii);
    setSelectedIds([sorted[0].id, sorted[sorted.length - 1].id]);
  };

  const calcCoolingPot = (z: ZoneProperties) =>
    Math.min(
      3.0,
      (z.available_land_pct / 10) * 0.35 +
        (z.roof_pct / 10) * 0.28 +
        (z.road_pct / 10) * 0.18,
    );

  const maxSuhii =
    selectedZones.length > 0
      ? Math.max(...selectedZones.map((z) => z.predicted_suhii))
      : 0;
  const minSuhii =
    selectedZones.length > 0
      ? Math.min(...selectedZones.map((z) => z.predicted_suhii))
      : 0;
  const suhiiDisparity = (maxSuhii - minSuhii).toFixed(1);

  return (
    <div className="zone-compare-page space-y-6">
      {/* Header toolbar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-gray-200">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-emerald-800">
            <Scale size={14} /> Multi-Zone Differential Analysis
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mt-1">Cross-Sector Heat & Vulnerability Comparison</h2>
          <p className="text-sm text-gray-600">Select up to 4 zones to evaluate spatial disparities and prioritize cooling interventions.</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Button variant="outline" onClick={selectTopHotspots}>
            <Sparkles size={14} className="text-amber-500" /> Top 3 Hotspots
          </Button>
          <Button variant="outline" onClick={selectExtremeContrast}>
            <Thermometer size={14} className="text-red-500" /> Extreme Contrast
          </Button>
        </div>
      </div>

      {/* Zone Selector Chips */}
      <div className="flex items-center gap-2 flex-wrap p-3 bg-gray-50 rounded-lg border border-gray-200">
        <span className="text-xs font-medium text-gray-500 uppercase mr-2">Active Zones ({selectedZones.length}/4):</span>
        {allZones.map((zone) => {
          const isSelected = selectedIds.includes(zone.id);
          return (
            <button
              key={zone.id}
              type="button"
              onClick={() => toggleZone(zone.id)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors flex items-center gap-1.5 ${
                isSelected
                  ? "bg-emerald-700 text-white shadow-sm"
                  : "bg-white text-gray-700 border border-gray-300 hover:bg-gray-100"
              }`}
            >
              {isSelected ? <Check size={12} /> : null}
              {zone.name} ({zone.id})
            </button>
          );
        })}
      </div>

      {/* Summary KPI Disparity Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-4 bg-white rounded-lg border border-gray-200">
          <div className="text-xs text-gray-500 font-medium">Thermal Disparity (ΔSUHII)</div>
          <div className="text-2xl font-bold text-red-600 mt-1">+{suhiiDisparity} °C</div>
          <div className="text-xs text-gray-500 mt-1">Difference between hottest and coolest compared zone</div>
        </div>
        <div className="card p-4 bg-white rounded-lg border border-gray-200">
          <div className="text-xs text-gray-500 font-medium">Combined Exposed Population</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">
            {fmt(selectedZones.reduce((acc, z) => acc + z.population, 0), 0)}
          </div>
          <div className="text-xs text-gray-500 mt-1">Total residents across {selectedZones.length} selected sectors</div>
        </div>
        <div className="card p-4 bg-white rounded-lg border border-gray-200">
          <div className="text-xs text-gray-500 font-medium">Max Cooling Potential</div>
          <div className="text-2xl font-bold text-emerald-600 mt-1">
            {selectedZones.length > 0 ? Math.max(...selectedZones.map(calcCoolingPot)).toFixed(2) : "0.00"} °C
          </div>
          <div className="text-xs text-gray-500 mt-1">Highest feasible surface-cooling accommodation</div>
        </div>
      </div>

      {/* Visual Bar Chart */}
      <ZoneComparisonChart zones={selectedZones} />

      {/* Comparison Metrics Table */}
      <div className="card bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="p-4 border-b border-gray-200">
          <h3 className="font-semibold text-gray-900">Side-by-Side Detailed Metric Comparison</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase">
                <th className="p-3 w-1/4">Indicator / Dimension</th>
                {selectedZones.map((zone) => (
                  <th key={zone.id} className="p-3">
                    {zone.name} <span className="text-gray-400 font-normal">({zone.id})</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {/* Thermal Profile */}
              <tr className="bg-emerald-50/40 text-emerald-900 font-semibold text-xs uppercase">
                <td colSpan={selectedZones.length + 1} className="p-2.5">Thermal Profile & Land Surface Temperature</td>
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">Predicted SUHII</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3">
                    <span className="font-semibold text-gray-900">{z.predicted_suhii.toFixed(1)} °C</span>
                    {z.hotspot && <Badge tone="red" className="ml-2">Hotspot</Badge>}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">Land Surface Temperature (LST)</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 text-gray-800">{z.predicted_lst.toFixed(1)} °C</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">95% Confidence Interval</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 text-xs text-gray-500">[{z.interval_low.toFixed(1)}, {z.interval_high.toFixed(1)}] °C</td>
                ))}
              </tr>

              {/* Surface & Vegetation */}
              <tr className="bg-emerald-50/40 text-emerald-900 font-semibold text-xs uppercase">
                <td colSpan={selectedZones.length + 1} className="p-2.5">Vegetation & Built-up Density</td>
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">NDVI (Vegetation Index)</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 text-gray-800">{z.ndvi.toFixed(3)}</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">NDBI (Built-up Index)</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 text-gray-800">{z.ndbi.toFixed(3)}</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">Building Density</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 text-gray-800">{(z.building_density * 100).toFixed(1)}%</td>
                ))}
              </tr>

              {/* Demographics & Risk */}
              <tr className="bg-emerald-50/40 text-emerald-900 font-semibold text-xs uppercase">
                <td colSpan={selectedZones.length + 1} className="p-2.5">Demographics & Vulnerability</td>
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">Exposed Population</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 text-gray-800">{fmt(z.population, 0)} residents</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">Elderly Share (65+)</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 text-gray-800">{(z.elderly_share * 100).toFixed(1)}%</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">Heat Risk Score</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3">
                    <Badge tone={z.risk_level === "High" ? "red" : z.risk_level === "Moderate" ? "orange" : "green"}>
                      {z.risk_score.toFixed(1)} · {z.risk_level}
                    </Badge>
                  </td>
                ))}
              </tr>

              {/* Intervention Capacities */}
              <tr className="bg-emerald-50/40 text-emerald-900 font-semibold text-xs uppercase">
                <td colSpan={selectedZones.length + 1} className="p-2.5">Intervention Capacity & Physical Constraints</td>
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">Available Unbuilt Ground</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 text-gray-800">{z.available_land_pct.toFixed(1)}%</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">Roof Area Capacity</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 text-gray-800">{z.roof_pct.toFixed(1)}%</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">Estimated Max Cooling Potential</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 font-semibold text-emerald-700">
                    {calcCoolingPot(z).toFixed(2)} °C
                  </td>
                ))}
              </tr>

              {/* Action Rows */}
              <tr className="bg-gray-50">
                <td className="p-3 font-medium text-gray-700">Planning Actions</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 space-y-1.5">
                    <Button
                      variant="outline"
                      className="text-xs w-full justify-start"
                      onClick={() => {
                        onSelect?.(z);
                        navigate("Intervention simulator", { zone: z.id });
                      }}
                    >
                      <ArrowRight size={12} className="mr-1" /> Simulate Interventions
                    </Button>
                    <Button
                      variant="outline"
                      className="text-xs w-full justify-start"
                      onClick={() => {
                        onSelect?.(z);
                        navigate("Explainable AI", { zone: z.id });
                      }}
                    >
                      <Sparkles size={12} className="mr-1" /> Inspect SHAP Drivers
                    </Button>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
```

---

### 3.3 Drop-In Replacement for `PAGE_MAP` in `frontend/src/lib/constants.ts`

Replace `PAGE_MAP` (lines 54–83) with:

```typescript
export const PAGE_MAP: Record<string, PageDefinition> = {
  // Overview
  overview: PAGES[0],
  Overview: PAGES[0],

  // Heat map
  map: PAGES[1],
  "Heat map": PAGES[1],
  Map: PAGES[1],
  maps: PAGES[1],
  Maps: PAGES[1],

  // Zone comparison
  compare: PAGES[2],
  "Zone comparison": PAGES[2],
  ZoneCompare: PAGES[2],
  comparison: PAGES[2],
  Comparison: PAGES[2],
  comparisons: PAGES[2],
  Comparisons: PAGES[2],

  // AI prediction
  prediction: PAGES[3],
  "AI prediction": PAGES[3],
  Prediction: PAGES[3],
  predictions: PAGES[3],
  Predictions: PAGES[3],

  // Explainable AI
  explain: PAGES[4],
  "Explainable AI": PAGES[4],
  Explain: PAGES[4],
  explanation: PAGES[4],
  Explanation: PAGES[4],
  explanations: PAGES[4],
  Explanations: PAGES[4],

  // Heat risk
  risk: PAGES[5],
  "Heat risk": PAGES[5],
  Risk: PAGES[5],
  risks: PAGES[5],
  Risks: PAGES[5],

  // Intervention simulator
  simulator: PAGES[6],
  "Intervention simulator": PAGES[6],
  Simulator: PAGES[6],
  simulation: PAGES[6],
  Simulation: PAGES[6],
  simulations: PAGES[6],
  Simulations: PAGES[6],

  // Optimization
  optimizer: PAGES[7],
  Optimization: PAGES[7],
  Optimizer: PAGES[7],
  optimize: PAGES[7],
  Optimize: PAGES[7],

  // AI assistant
  assistant: PAGES[8],
  "AI assistant": PAGES[8],
  Assistant: PAGES[8],
  assistants: PAGES[8],
  Assistants: PAGES[8],

  // Reports
  reports: PAGES[9],
  Reports: PAGES[9],
  report: PAGES[9],
  Report: PAGES[9],
};
```

---

### 3.4 Recommended Hardening for `frontend/src/hooks/useHashRouter.ts`

In `useHashRouter.ts` line 75:
```typescript
  const setCity = useCallback(
    (city: City) => {
      // Clear zoneId when switching cities to ensure clean URL params
      navigate({ city, zoneId: "" });
    },
    [navigate],
  );
```
This guarantees that switching cities in the Topbar cleanses stale zone query parameters from the browser location hash.

---

### 3.5 Critical Test Alignment Notice for Worker M1-Iter2

In `frontend/src/tests/integration_challenge.test.ts`:
Line 79 currently contains a test originally written to verify that the bug was present:
```typescript
  it("BUG DEMONSTRATION: #/predictions (plural) fails to resolve and falls back to overview", () => {
    const result = simulateParseHash("#/predictions");
    expect(result.page).toBe("overview");
    expect(PAGE_MAP["predictions"]).toBeUndefined();
  });
```
**CRITICAL:** Once `predictions: PAGES[3]` is added to `PAGE_MAP`, this test will **FAIL** because `PAGE_MAP["predictions"]` is now defined and resolves to `"prediction"`.
The Worker **must update** this test in `integration_challenge.test.ts` to assert the resolved behavior:
```typescript
  it("resolves plural route aliases correctly (e.g., #/predictions and #/simulations)", () => {
    const predResult = simulateParseHash("#/predictions");
    expect(predResult.page).toBe("prediction");
    expect(PAGE_MAP["predictions"]).toBeDefined();

    const simResult = simulateParseHash("#/simulations");
    expect(simResult.page).toBe("simulator");
    expect(PAGE_MAP["simulations"]).toBeDefined();
  });
```

Similarly, if the Worker addresses Challenger's `apiClient.ts` recommendations (wrapping `fetch` and `response.json()` in try/catch to throw `ApiError`), lines 347 and 368 in `integration_challenge.test.ts` must be updated to expect `expect(err).toBeInstanceOf(ApiError)` rather than `SyntaxError` / `TypeError`.

---

## 4. Verification Plan

1. **Vitest Unit & Integration Suites:**
   ```bash
   cd frontend
   npm test -- --run
   ```
   All test files (including `metrics.test.ts`, `weather.test.ts`, `zoneCompare.test.ts`, and `integration_challenge.test.ts`) must pass with 0 errors.

2. **TypeScript & Production Build Verification:**
   ```bash
   cd frontend
   npm run build
   ```
   Must execute `tsc -b && vite build` and exit code 0.

3. **Line Count Constraint Check:**
   `frontend/src/App.tsx` must remain under 150 lines (proposed implementation is 95 lines).
