import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { evidenceService } from "../services/evidenceService";
import type {
  City,
  EvidenceAsset,
  EvidenceAssetSummary,
  EvidenceLayer,
  EvidenceProvenance,
  WorkspaceResponse,
} from "../types";
import { EvidenceLayerPreview } from "../components/evidence/EvidenceLayerPreview";

function showValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Not supplied";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function Provenance({ provenance }: { provenance: EvidenceProvenance }) {
  return (
    <dl style={{ display: "grid", gap: "5px 12px", gridTemplateColumns: "max-content minmax(0, 1fr)", margin: "14px 0 0" }}>
      <dt>Kind / status</dt><dd style={{ margin: 0 }}>{provenance.kind} · {provenance.status}</dd>
      <dt>Freshness</dt><dd style={{ margin: 0 }}>{provenance.freshness}</dd>
      <dt>Retrieved</dt><dd style={{ margin: 0 }}>{showValue(provenance.retrieved_at)}</dd>
      <dt>Observation time</dt><dd style={{ margin: 0 }}>{showValue(provenance.observation_time)}</dd>
      <dt>Coverage / resolution</dt><dd style={{ margin: 0 }}>{showValue(provenance.coverage)} · {showValue(provenance.resolution)}</dd>
      <dt>Units</dt><dd style={{ margin: 0 }}>{showValue(provenance.units)}</dd>
      <dt>Processing</dt><dd style={{ margin: 0 }}>{showValue(provenance.processing)}</dd>
      <dt>Quality</dt><dd style={{ margin: 0 }}>{showValue(provenance.quality)}</dd>
      <dt>Analysis ready</dt><dd style={{ margin: 0 }}>{provenance.analysis_ready ? "Yes" : "No"}</dd>
      {provenance.limitations.length > 0 && (
        <>
          <dt>Limitations</dt>
          <dd style={{ margin: 0 }}>
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {provenance.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}
            </ul>
          </dd>
        </>
      )}
    </dl>
  );
}

function AssetCard({
  asset,
  selected,
  onInspect,
}: {
  asset: EvidenceAssetSummary;
  selected: boolean;
  onInspect: () => void;
}) {
  return (
    <article className="card" style={{ padding: 18 }}>
      <div style={{ alignItems: "flex-start", display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "space-between" }}>
        <div>
          <h3>{asset.source} · {asset.category}</h3>
          <p className="muted" style={{ overflowWrap: "anywhere", marginTop: 4 }}>
            {asset.id} · {asset.mode} evidence · {asset.analysis_ready ? "analysis ready" : "not analysis ready"}
          </p>
        </div>
        <button
          type="button"
          aria-expanded={selected}
          aria-controls={`asset-detail-${encodeURIComponent(asset.id)}`}
          onClick={onInspect}
          style={{ background: "#eaf2e9", borderRadius: 6, color: "#2d6e52", fontWeight: 700, padding: "8px 11px" }}
        >
          {selected ? "Hide payload" : "Inspect payload"}
        </button>
      </div>
      <Provenance provenance={asset.provenance} />
    </article>
  );
}

function AssetDetail({
  asset,
  assetId,
  isLoading,
  error,
}: {
  asset?: EvidenceAsset;
  assetId: string;
  isLoading: boolean;
  error?: string;
}) {
  return (
    <section
      className="card"
      id={`asset-detail-${encodeURIComponent(assetId)}`}
      aria-live="polite"
      style={{ borderColor: "#b9d1bd", marginTop: 12, padding: 18 }}
    >
      <h3>Acquired payload · {assetId}</h3>
      {isLoading && <p className="muted" style={{ marginTop: 8 }}>Loading the acquired asset detail…</p>}
      {error && <p role="alert" style={{ color: "#9b3434", marginTop: 8 }}>{error}</p>}
      {asset && (
        <>
          <p className="muted" style={{ marginTop: 8 }}>
            Payload returned for this asset. Provenance remains {asset.mode} and analysis ready: {asset.analysis_ready ? "yes" : "no"}.
          </p>
          <pre style={{ background: "#f6f8f5", borderRadius: 6, margin: "10px 0 0", maxHeight: 420, overflow: "auto", padding: 12, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
            {JSON.stringify(asset.payload, null, 2)}
          </pre>
        </>
      )}
    </section>
  );
}

function LayerCard({ layer }: { layer: EvidenceLayer }) {
  const isWeatherAirTemperature = /air.?temperature|temperature_2m/i.test(`${layer.name} ${layer.variable}`);
  return (
    <article className="card" style={{ padding: 18 }}>
      <div style={{ alignItems: "flex-start", display: "flex", gap: 12, justifyContent: "space-between" }}>
        <div>
          <h3>{layer.name}</h3>
          <p className="muted" style={{ marginTop: 4 }}>{layer.variable} · {layer.kind}{layer.unit ? ` · ${layer.unit}` : ""}</p>
        </div>
        <span
          aria-label={`Layer ${layer.status}`}
          style={{
            background: layer.status === "available" ? "#e5f2e7" : "#f2eeee",
            borderRadius: 999,
            color: layer.status === "available" ? "#27633c" : "#765858",
            flexShrink: 0,
            fontSize: 12,
            fontWeight: 700,
            padding: "5px 9px",
          }}
        >
          {layer.status}
        </span>
      </div>
      {layer.source && <p style={{ marginTop: 10 }}>Source: {layer.source}</p>}
      <p className="muted" style={{ marginTop: 5 }}>
        Observation: {showValue(layer.observation_time)} · Retrieved: {showValue(layer.retrieved_at)} · Resolution: {showValue(layer.resolution)}
      </p>
      {layer.reason && <p className="muted" style={{ marginTop: 8 }}>Reason: {layer.reason}</p>}
      {!layer.reason && layer.status === "unavailable" && (
        <p className="muted" style={{ marginTop: 8 }}>No additional unavailability reason was supplied.</p>
      )}
      {layer.status === "available" && (
        <div style={{ marginTop: 12 }}>
          <EvidenceLayerPreview layer={layer} />
        </div>
      )}
      {isWeatherAirTemperature && (
        <p className="muted" style={{ borderLeft: "3px solid #d5a755", marginTop: 12, paddingLeft: 10 }}>
          Atmospheric air temperature is not satellite Land Surface Temperature (LST).
        </p>
      )}
      {layer.limitations.length > 0 && (
        <ul className="muted" style={{ margin: "10px 0 0", paddingLeft: 18 }}>
          {layer.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}
        </ul>
      )}
    </article>
  );
}

export interface EvidenceWorkspaceContentProps {
  workspace: WorkspaceResponse;
  selectedAssetId?: string;
  selectedAsset?: EvidenceAsset;
  isAssetLoading?: boolean;
  assetError?: string;
  onInspectAsset: (assetId: string) => void;
}

export function EvidenceWorkspaceContent({
  workspace,
  selectedAssetId,
  selectedAsset,
  isAssetLoading = false,
  assetError,
  onInspectAsset,
}: EvidenceWorkspaceContentProps) {
  const liveAssets = workspace.assets.filter((asset) => asset.mode === "live");
  return (
    <div style={{ display: "grid", gap: 20 }}>
      <header>
        <p style={{ color: "#6d7f72", fontSize: 11, fontWeight: 700, letterSpacing: 1.1, textTransform: "uppercase" }}>
          Acquired evidence · {workspace.city}
        </p>
        <h1 style={{ marginTop: 5 }}>Evidence workspace</h1>
        <section
          className="card"
          role="status"
          style={{ background: "#fff9e9", borderColor: "#ead7a6", marginTop: 14, padding: 18 }}
        >
          <h2 style={{ fontSize: 18 }}>Heat analysis unavailable</h2>
          <p style={{ marginTop: 6 }}>
            {workspace.analysis.reason || "No validated analysis dataset is available for this workspace."}
          </p>
          <p className="muted" style={{ marginTop: 5 }}>
            This normal-mode view contains acquired evidence only. It does not create synthetic map geometry, heat scores, or recommendations.
          </p>
          {workspace.limitations.length > 0 && (
            <ul style={{ margin: "8px 0 0", paddingLeft: 20 }}>
              {workspace.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}
            </ul>
          )}
        </section>
      </header>

      <section aria-labelledby="evidence-assets-heading">
        <div className="section-toolbar">
          <div>
            <h2 id="evidence-assets-heading" style={{ fontSize: 19 }}>Acquired assets</h2>
            <p className="muted">Live source records and provenance; payloads are fetched only when requested.</p>
          </div>
          <span>{liveAssets.length} live asset{liveAssets.length === 1 ? "" : "s"}</span>
        </div>
        {liveAssets.length === 0 ? (
          <div className="empty small">No live acquired assets are recorded for {workspace.city}.</div>
        ) : (
          <div style={{ display: "grid", gap: 12, marginTop: 12 }}>
            {liveAssets.map((asset) => (
              <AssetCard
                key={asset.id}
                asset={asset}
                selected={selectedAssetId === asset.id}
                onInspect={() => onInspectAsset(asset.id)}
              />
            ))}
          </div>
        )}
        {workspace.assets.length > liveAssets.length && (
          <p className="muted" style={{ marginTop: 8 }}>
            {workspace.assets.length - liveAssets.length} non-live asset record{workspace.assets.length - liveAssets.length === 1 ? " is" : "s are"} excluded from this normal-mode view.
          </p>
        )}
        {selectedAssetId && (
          <AssetDetail
            asset={selectedAsset}
            assetId={selectedAssetId}
            isLoading={isAssetLoading}
            error={assetError}
          />
        )}
      </section>

      <section aria-labelledby="evidence-layers-heading">
        <div className="section-toolbar">
          <div>
            <h2 id="evidence-layers-heading" style={{ fontSize: 19 }}>Evidence layers</h2>
            <p className="muted">Availability reflects acquired, mappable evidence—not inferred coverage.</p>
          </div>
          <span>{workspace.layers.length} layer{workspace.layers.length === 1 ? "" : "s"}</span>
        </div>
        {workspace.layers.length === 0 ? (
          <div className="empty small">No evidence layers are registered for this workspace.</div>
        ) : (
          <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 340px), 1fr))", marginTop: 12 }}>
            {workspace.layers.map((layer) => <LayerCard key={layer.id} layer={layer} />)}
          </div>
        )}
      </section>
    </div>
  );
}

export function EvidenceWorkspacePage({ city, workspace }: { city: City; workspace: WorkspaceResponse }) {
  const [selectedAssetId, setSelectedAssetId] = useState<string>();
  const assetQuery = useQuery({
    queryKey: ["evidence-asset", city, selectedAssetId],
    queryFn: () => evidenceService.getAsset(selectedAssetId as string, city),
    enabled: Boolean(selectedAssetId),
  });

  const handleInspect = (assetId: string) => {
    setSelectedAssetId((current) => current === assetId ? undefined : assetId);
  };

  return (
    <EvidenceWorkspaceContent
      workspace={workspace}
      selectedAssetId={selectedAssetId}
      selectedAsset={assetQuery.data}
      isAssetLoading={assetQuery.isFetching}
      assetError={assetQuery.error instanceof Error ? assetQuery.error.message : undefined}
      onInspectAsset={handleInspect}
    />
  );
}
