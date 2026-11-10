import React, { useState, useEffect } from "react";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import type { City, ZoneFeature, ZoneProperties } from "./types";
import { heatService, dataService } from "./services";
import { useHashRouter } from "./hooks/useHashRouter";
import { Sidebar, Topbar } from "./components/layout";
import { Pending } from "./components/common/Pending";
import { NoAnalysisState } from "./components/common/NoAnalysisState";
import { DataDialog } from "./components/modals/DataDialog";
import { evidenceService } from "./services/evidenceService";
import { NormalModeContent } from "./pages/NormalModeContent";
import {
  OverviewPage, MapPage, PredictionsPage, EnvironmentalPage, ExplainPage, RiskPage,
  SimulatorPage, OptimizerPage, AssistantPage, ReportsPage, ZoneComparePage,
} from "./pages";

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } },
});

function isDemoModeStored(): boolean {
  try {
    return typeof window !== "undefined" &&
      window.sessionStorage.getItem("heatwise-mode") === "demo";
  } catch {
    return false;
  }
}

function HeatwiseApp() {
  const { page, city, zoneId, layer, navigate, setCity, setLayer } = useHashRouter();
  const [showData, setShowData] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);
  const [selectedZone, setSelectedZone] = useState<ZoneProperties | null>(null);
  const [isDemoMode, setIsDemoMode] = useState(isDemoModeStored);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const notify = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 4000);
  };

  const health = useQuery({ queryKey: ["health"], queryFn: heatService.getHealth });
  const status = useQuery({ queryKey: ["status"], queryFn: dataService.getDataStatus });
  const evidenceWorkspace = useQuery({
    queryKey: ["evidence-workspace", city],
    queryFn: () => evidenceService.getWorkspace(city),
    enabled: !isDemoMode,
  });
  const analysisEnabled = isDemoMode || evidenceWorkspace.data?.analysis.status === "available";
  const overview = useQuery({
    queryKey: ["overview", city],
    queryFn: () => heatService.getOverview(city),
    enabled: analysisEnabled,
  });
  const data = useQuery({
    queryKey: ["map", city],
    queryFn: () => heatService.getHeatMap(city),
    enabled: analysisEnabled,
  });

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

  const exitDemoMode = () => {
    try {
      if (typeof window !== "undefined") {
        window.sessionStorage.removeItem("heatwise-mode");
      }
    } catch {
      // Session storage may be unavailable in restricted browser contexts.
    }
    setIsDemoMode(false);
    void queryClient.invalidateQueries();
  };

  return (
    <div className="layout">
      <Sidebar
        currentPage={page}
        onNavigate={navigate}
        city={city}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
        isMobileOpen={isMobileOpen}
        onCloseMobile={() => setIsMobileOpen(false)}
      />
      <div className={`main ${isSidebarCollapsed ? "sidebar-collapsed" : "sidebar-expanded"}`}>
        <Topbar
          city={city}
          onCityChange={(c: City) => setCity(c)}
          onOpenData={() => setShowData(true)}
          databaseStatus={health.data?.database}
          isSynthetic={Boolean(data.data?.metadata?.isSynthetic ?? data.data?.metadata?.synthetic)}
          onNavigate={navigate}
          onSelectZone={(zId) => navigate({ zoneId: zId })}
          onSelectLayer={(l) => setLayer(l)}
          zones={data.data?.features}
          onToggleSidebar={() => {
            if (typeof window !== "undefined" && window.innerWidth < 768) {
              setIsMobileOpen((prev) => !prev);
            } else {
              setIsSidebarCollapsed((prev) => !prev);
            }
          }}
          isSidebarCollapsed={isSidebarCollapsed}
        />
        {isDemoMode && (
          <div
            role="status"
            aria-live="polite"
            style={{
              alignItems: "center",
              background: "#fff4d6",
              border: "1px solid #e8c66a",
              borderRadius: 8,
              color: "#674c00",
              display: "flex",
              gap: 12,
              justifyContent: "space-between",
              margin: "12px 24px 0",
              padding: "10px 14px",
            }}
          >
            <span><strong>Demo mode is active.</strong> Analysis uses synthetic demonstration data.</span>
            <button
              type="button"
              onClick={exitDemoMode}
              style={{
                background: "#674c00",
                borderRadius: 5,
                color: "#fff",
                flexShrink: 0,
                fontWeight: 700,
                padding: "7px 10px",
              }}
            >
              Exit demo mode
            </button>
          </div>
        )}
        {notification && <div className="toast-notification">{notification}</div>}

        <main className="content">
          {isDemoMode ? (
            overview.isError || data.isError ? (
              <NoAnalysisState
                onOpenData={() => setShowData(true)}
                message={
                  overview.error instanceof Error
                    ? overview.error.message
                    : data.error instanceof Error
                      ? data.error.message
                      : undefined
                }
              />
            ) : !overview.data || !data.data || !activeZone ? (
              <Pending message={`Loading spatial intelligence for ${city}…`} />
            ) : (
              <>
                {page === "overview" && <OverviewPage city={city} overview={overview.data} data={data.data} selected={activeZone} onSelect={handleSelectZone} layer={layer} onLayer={setLayer} navigate={navigate} />}
                {page === "map" && <MapPage city={city} data={data.data} overview={overview.data} selected={activeZone} onSelect={handleSelectZone} layer={layer} onLayer={setLayer} navigate={navigate} />}
                {page === "compare" && <ZoneComparePage key={city} city={city} data={data.data} selected={activeZone} onSelect={handleSelectZone} navigate={navigate} notify={notify} />}
                {(page === "prediction" || page === "heat") && <PredictionsPage city={city} data={data.data} overview={overview.data} notify={notify} onOpenDataDialog={() => setShowData(true)} />}
                {page === "environmental" && <EnvironmentalPage city={city} onOpenDataDialog={() => setShowData(true)} />}
                {page === "explain" && <ExplainPage city={city} data={data.data} selected={activeZone} onSelect={handleSelectZone} overview={overview.data} />}
                {page === "risk" && <RiskPage city={city} data={data.data} selected={activeZone} onSelect={handleSelectZone} />}
                {page === "simulator" && <SimulatorPage city={city} data={data.data} selected={activeZone} onSelect={handleSelectZone} notify={notify} />}
                {page === "optimizer" && <OptimizerPage city={city} overview={overview.data} notify={notify} />}
                {page === "assistant" && <AssistantPage city={city} data={data.data} selected={activeZone} onSelect={handleSelectZone} navigate={navigate} />}
                {page === "reports" && <ReportsPage city={city} overview={overview.data} status={status.data} notify={notify} />}
              </>
            )
          ) : (
            <NormalModeContent
              city={city}
              workspace={evidenceWorkspace.data}
              isLoading={evidenceWorkspace.isLoading}
              error={evidenceWorkspace.isError
                ? (evidenceWorkspace.error instanceof Error
                  ? evidenceWorkspace.error.message
                  : String(evidenceWorkspace.error))
                : undefined}
              onOpenData={() => setShowData(true)}
            >
              {overview.isError || data.isError ? (
                <NoAnalysisState
                  onOpenData={() => setShowData(true)}
                  message={
                    overview.error instanceof Error
                      ? overview.error.message
                      : data.error instanceof Error
                        ? data.error.message
                        : undefined
                  }
                />
              ) : !overview.data || !data.data || !activeZone ? (
                <Pending message={`Loading spatial intelligence for ${city}…`} />
              ) : (
                <>
                  {page === "overview" && <OverviewPage city={city} overview={overview.data} data={data.data} selected={activeZone} onSelect={handleSelectZone} layer={layer} onLayer={setLayer} navigate={navigate} />}
                  {page === "map" && <MapPage city={city} data={data.data} overview={overview.data} selected={activeZone} onSelect={handleSelectZone} layer={layer} onLayer={setLayer} navigate={navigate} />}
                  {page === "compare" && <ZoneComparePage key={city} city={city} data={data.data} selected={activeZone} onSelect={handleSelectZone} navigate={navigate} notify={notify} />}
                  {(page === "prediction" || page === "heat") && <PredictionsPage city={city} data={data.data} overview={overview.data} notify={notify} onOpenDataDialog={() => setShowData(true)} />}
                  {page === "environmental" && <EnvironmentalPage city={city} onOpenDataDialog={() => setShowData(true)} />}
                  {page === "explain" && <ExplainPage city={city} data={data.data} selected={activeZone} onSelect={handleSelectZone} overview={overview.data} />}
                  {page === "risk" && <RiskPage city={city} data={data.data} selected={activeZone} onSelect={handleSelectZone} />}
                  {page === "simulator" && <SimulatorPage city={city} data={data.data} selected={activeZone} onSelect={handleSelectZone} notify={notify} />}
                  {page === "optimizer" && <OptimizerPage city={city} overview={overview.data} notify={notify} />}
                  {page === "assistant" && <AssistantPage city={city} data={data.data} selected={activeZone} onSelect={handleSelectZone} navigate={navigate} />}
                  {page === "reports" && <ReportsPage city={city} overview={overview.data} status={status.data} notify={notify} />}
                </>
              )}
            </NormalModeContent>
          )}
        </main>
      </div>

      {showData && (
        <DataDialog
          city={city}
          close={() => setShowData(false)}
          notify={notify}
          onDemoMode={() => setIsDemoMode(true)}
        />
      )}
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
