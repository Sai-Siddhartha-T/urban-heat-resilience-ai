import { useState, type ReactNode } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowDown,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CloudSun,
  Database,
  FileText,
  FlaskConical,
  Globe2,
  LayoutDashboard,
  Leaf,
  Map,
  MapPin,
  Menu,
  MessageSquare,
  Network,
  RefreshCw,
  Search,
  Send,
  Settings2,
  ShieldCheck,
  Sparkles,
  Sun,
  Target,
  Thermometer,
  TreePine,
  Users,
  X,
  TriangleAlert,
  Zap,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ScatterChart,
  Scatter,
  ReferenceLine,
} from "recharts";
import HeatMap from "./components/HeatMap";
import { Button } from "./components/button";
import { api, download, fmt, label } from "./api";
const pages = [
  ["Overview", LayoutDashboard],
  ["Heat map", Map],
  ["AI prediction", Activity],
  ["Explainable AI", Network],
  ["Heat risk", ShieldCheck],
  ["Intervention simulator", TreePine],
  ["Optimization", Target],
  ["AI assistant", Sparkles],
  ["Reports", FileText],
] as const;
const interventionNames: Record<string, string> = {
  trees: "Urban trees",
  vegetation: "Native vegetation",
  parks: "Pocket parks",
  cool_roofs: "Cool roofs",
  pavements: "Reflective pavements",
  corridors: "Green corridors",
  roof_gardens: "Rooftop gardens",
  water: "Water-based cooling",
};
function Notice({
  children,
  error = false,
}: {
  children: ReactNode;
  error?: boolean;
}) {
  return (
    <div className={"notice " + (error ? "error" : "")}>
      <TriangleAlert size={15} />
      <span>{children}</span>
    </div>
  );
}
function Pending() {
  return (
    <div className="empty">
      <RefreshCw className="spin" size={24} />
      <span>Computing your analysis…</span>
    </div>
  );
}
function Badge({
  children,
  tone = "green",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={"badge " + tone}>{children}</span>;
}
function Card({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={"card " + className}>
      {title && (
        <div className="card-heading">
          <div>
            <h3>{title}</h3>
            {subtitle && <p>{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}
function Metric({
  label,
  value,
  unit,
  detail,
  icon: Icon,
  tone = "green",
}: any) {
  return (
    <Card className="metric">
      <div className="metric-top">
        <span>{label}</span>
        <div className={"metric-icon " + tone}>
          <Icon size={18} />
        </div>
      </div>
      <div className="metric-value">
        {value}
        <span>{unit}</span>
      </div>
      <div className="metric-detail">{detail}</div>
    </Card>
  );
}
function ZonePicker({ data, selected, onSelect }: any) {
  return (
    <select
      className="select zone-picker"
      aria-label="Analysis zone"
      value={selected?.id || ""}
      onChange={(e) =>
        onSelect(
          data.features.find((f: any) => f.properties.id === e.target.value)
            .properties,
        )
      }
    >
      {data.features.map((f: any) => (
        <option key={f.properties.id} value={f.properties.id}>
          {f.properties.name}
        </option>
      ))}
    </select>
  );
}
export default function App() {
  const [page, setPage] = useState("Overview"),
    [city, setCity] = useState("Ahmedabad"),
    [selectedId, setSelectedId] = useState(""),
    [layer, setLayer] = useState("predicted_suhii"),
    [drawer, setDrawer] = useState(false),
    [dataOpen, setDataOpen] = useState(false),
    [tokenOpen, setTokenOpen] = useState(false),
    [toast, setToast] = useState("");
  const overview = useQuery({
    queryKey: ["overview", city],
    queryFn: () => api("/overview?city=" + city),
  });
  const map = useQuery({
    queryKey: ["map", city],
    queryFn: () => api("/heat/map?city=" + city),
  });
  const status = useQuery({
    queryKey: ["status"],
    queryFn: () => api("/data/status"),
  });
  const selected =
    map.data?.features.find((f: any) => f.properties.id === selectedId)
      ?.properties || overview.data?.priority_zones[0];
  const notify = (s: string) => {
    setToast(s);
    setTimeout(() => setToast(""), 5000);
  };
  const exportReport = useMutation({
    mutationFn: () => api("/reports/generate", { city }),
    onSuccess: async (r) => {
      try {
        await download(r.markdown_url, "heatwise-report.md");
        notify("Analysis report downloaded.");
      } catch (e: any) {
        notify(e.message);
      }
    },
  });
  function navigate(p: string) {
    setPage(p);
    setDrawer(false);
  }
  const common = {
    city,
    data: map.data,
    overview: overview.data,
    selected,
    onSelect: (p: any) => setSelectedId(p.id),
    notify,
  };
  return (
    <div className="app">
      <aside className={"sidebar " + (drawer ? "open" : "")}>
        <a className="brand" href="#" onClick={() => navigate("Overview")}>
          <span className="brand-symbol">
            <Sun size={23} />
          </span>
          <span>
            heatwise<span className="brand-dot">.</span>
            <small>URBAN CLIMATE INTELLIGENCE</small>
          </span>
        </a>
        <div className="workspace-label">
          WORKSPACE <span>RESEARCH</span>
        </div>
        <nav aria-label="Main navigation">
          {pages.map(([p, Icon], i) => (
            <div key={p}>
              {i === 5 && <div className="nav-divider">PLAN & ACT</div>}
              <button
                aria-label={p}
                className={"nav-item " + (page === p ? "active" : "")}
                onClick={() => navigate(p)}
              >
                <Icon size={18} />
                <span>{p}</span>
                {p === "AI assistant" && <span className="tiny-spark">✦</span>}
              </button>
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="city-card">
            <div className="city-card-icon">
              <Globe2 size={22} />
            </div>
            <strong>
              Cooler cities.
              <br />
              Stronger communities.
            </strong>
            <p>
              Turn climate insights into
              <br />
              thoughtful action.
            </p>
            <span>
              Built for a resilient future <Leaf size={12} />
            </span>
          </div>
          <button className="nav-item" onClick={() => setDataOpen(true)}>
            <Database size={17} />
            Data & sources
            <span className="status-dot" />
          </button>
          <button className="nav-item" onClick={() => setTokenOpen(true)}>
            <Settings2 size={17} />
            Workspace settings
          </button>
          <div className="profile">
            <div className="avatar">CP</div>
            <div>
              <strong>City planner</strong>
              <small>Research workspace</small>
            </div>
            <ChevronDown size={15} />
          </div>
        </div>
      </aside>
      {drawer && (
        <button
          className="scrim"
          aria-label="Close navigation"
          onClick={() => setDrawer(false)}
        />
      )}
      <div className="main">
        <header className="topbar">
          <div className="breadcrumbs">
            <button
              className="mobile-menu"
              aria-label="Open navigation"
              onClick={() => setDrawer(true)}
            >
              <Menu size={20} />
            </button>
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>{page}</strong>
          </div>
          <div className="top-actions">
            <span className="demo-pill">
              <span />
              Demonstration workspace
            </span>
            <button className="help-link" onClick={() => navigate("Reports")}>
              <BookOpen size={16} />
              <span>Methodology</span>
            </button>
            <div className="avatar small">CP</div>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">URBAN HEAT INTELLIGENCE</div>
              <h1>
                {page === "Overview"
                  ? "A clearer view of a warmer city."
                  : page}
              </h1>
              <p>
                {page === "Overview"
                  ? "Understand heat. Identify priorities. Plan a cooler tomorrow."
                  : (
                      {
                        "Heat map":
                          "Explore surface heat and the urban landscape, one zone at a time.",
                        "AI prediction":
                          "Compare genuine models with transparent spatial evaluation.",
                        "Explainable AI":
                          "Understand the factors behind each model prediction.",
                        "Heat risk":
                          "Bring exposure and vulnerability into the planning conversation.",
                        "Intervention simulator":
                          "Explore the possibilities. Make your assumptions explicit.",
                        Optimization:
                          "Find feasible interventions within land and water limits.",
                        "AI assistant":
                          "Turn structured evidence into a practical planning conversation.",
                        Reports:
                          "Take the evidence, methodology, and limitations with you.",
                      } as Record<string, string>
                    )[page]}
              </p>
            </div>
            <div className="heading-actions">
              <div className="location-select">
                <MapPin size={16} />
                <select
                  aria-label="City"
                  value={city}
                  onChange={(e) => {
                    setCity(e.target.value);
                    setSelectedId("");
                  }}
                >
                  <option>Ahmedabad</option>
                  <option>Delhi</option>
                  <option>Hyderabad</option>
                </select>
              </div>
              <Button
                variant="outline"
                onClick={() => exportReport.mutate()}
                disabled={exportReport.isPending}
              >
                <ArrowDownToLine size={15} />
                {exportReport.isPending ? "Preparing…" : "Export report"}
              </Button>
            </div>
          </div>
          <div className="context-bar">
            <div>
              <span className="live-dot" />
              <strong>Synthetic analysis</strong>
              <span className="context-sep" />
              Sample period: 15 May 2025
              <span className="context-sep" />1 km analysis grid
            </div>
            <button onClick={() => setDataOpen(true)}>
              View data provenance <ArrowUpRight size={13} />
            </button>
          </div>
          {(overview.isError || map.isError) && (
            <Notice error>
              {(overview.error || map.error)?.message}
              <Button
                variant="outline"
                onClick={() => {
                  overview.refetch();
                  map.refetch();
                }}
              >
                Retry
              </Button>
            </Notice>
          )}
          {overview.isPending || map.isPending ? (
            <Pending />
          ) : overview.data && map.data && selected ? (
            <>
              {page === "Overview" && (
                <Overview
                  {...common}
                  layer={layer}
                  onLayer={setLayer}
                  navigate={navigate}
                />
              )}
              {page === "Heat map" && (
                <div className="map-page">
                  <Card>
                    <HeatMap
                      {...common}
                      selected={selected.id}
                      layer={layer}
                      onLayer={setLayer}
                      tall
                    />
                  </Card>
                  <ZoneDetails selected={selected} navigate={navigate} />
                </div>
              )}
              {page === "AI prediction" && (
                <Prediction key={city} {...common} />
              )}
              {page === "Explainable AI" && <Explain key={city} {...common} />}
              {page === "Heat risk" && <Risk key={city} {...common} />}
              {page === "Intervention simulator" && (
                <Simulator key={city} {...common} />
              )}
              {page === "Optimization" && <Optimizer key={city} {...common} />}
              {page === "AI assistant" && <Assistant {...common} key={city} />}
              {page === "Reports" && (
                <Reports {...common} status={status.data} />
              )}
            </>
          ) : null}
          <footer>
            <span>
              <span className="footer-mark">✳</span> Heatwise · Climate
              intelligence, thoughtfully applied.
            </span>
            <span>
              Surface heat ≠ air temperature <span className="context-sep" />{" "}
              Prototype v0.1
            </span>
          </footer>
        </main>
      </div>
      {dataOpen && (
        <DataDialog
          city={city}
          close={() => setDataOpen(false)}
          notify={notify}
        />
      )}
      {tokenOpen && (
        <div className="modal-backdrop">
          <div className="modal small-modal">
            <button
              className="modal-close"
              aria-label="Close settings"
              onClick={() => setTokenOpen(false)}
            >
              <X />
            </button>
            <h2>Workspace settings</h2>
            <p>
              If the backend requires an API token, enter it for this browser
              session. Provider keys belong only in the server environment.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                sessionStorage.setItem(
                  "heatwise-token",
                  String(f.get("token")),
                );
                window.location.reload();
              }}
            >
              <label>
                Backend access token
                <input type="password" name="token" autoComplete="off" />
              </label>
              <Button>Save session token</Button>
            </form>
          </div>
        </div>
      )}
      {(toast || exportReport.isError) && (
        <div role="status" className="toast">
          {toast || exportReport.error?.message}
          <button
            aria-label="Dismiss notification"
            onClick={() => {
              setToast("");
              exportReport.reset();
            }}
          >
            <X size={15} />
          </button>
        </div>
      )}
    </div>
  );
}
function Overview({
  overview: o,
  data,
  selected,
  onSelect,
  layer,
  onLayer,
  navigate,
}: any) {
  return (
    <>
      <div className="metrics-grid">
        <Metric
          label="Area analyzed"
          value={fmt(o.area_km2, 0)}
          unit="km²"
          icon={Map}
          detail={`${o.zone_count} geographical zones`}
        />
        <Metric
          label="Average surface heat"
          value={"+" + fmt(o.average_suhii)}
          unit="°C"
          icon={Thermometer}
          tone="orange"
          detail="SUHII · relative to rural reference"
        />
        <Metric
          label="Heat hotspots"
          value={o.hotspots}
          unit="zones"
          icon={Sun}
          tone="red"
          detail={
            <>
              <span className="dot orange" />
              Predicted SUHII ≥ 4°C
            </>
          }
        />
        <Metric
          label="Population in high-risk zones"
          value={fmt(o.population_exposed / 1000, 0)}
          unit="k"
          icon={Users}
          tone="blue"
          detail="Synthetic population · priority proxy"
        />
      </div>
      <div className="overview-main">
        <Card
          title="The city's heat landscape"
          subtitle="Explore patterns. Select a grid cell for a closer look."
          action={
            <button
              className="text-button"
              onClick={() => navigate("Heat map")}
            >
              Explore map <ArrowUpRight size={15} />
            </button>
          }
        >
          <HeatMap
            data={data}
            selected={selected.id}
            onSelect={onSelect}
            layer={layer}
            onLayer={onLayer}
          />
          <div className="map-foot">
            <span>
              <span className="dot red" />
              {o.high_risk_zones} zones flagged as high risk
            </span>
            <span>Illustrative grid · WGS84</span>
          </div>
        </Card>
        <div className="insight-column">
          <section className="insight-card">
            <div className="insight-title">
              <Sparkles size={17} />
              <span>FROM THE EVIDENCE</span>
              <Badge tone="mint">MODEL INSIGHTS</Badge>
            </div>
            <h2>
              Every hotspot
              <br />
              has a story.
            </h2>
            <p>
              Your model identifies{" "}
              <strong>{label(o.importance[0].feature).toLowerCase()}</strong> as
              the strongest association with surface heat in this sample.
            </p>
            <div className="insight-divider" />
            <div className="insight-point">
              <span>
                <TreePine size={17} />
              </span>
              <div>
                <strong>Start with the landscape</strong>
                <p>
                  Explore vegetation and built-up surfaces alongside local model
                  contributions.
                </p>
              </div>
            </div>
            <div className="insight-point">
              <span>
                <Target size={17} />
              </span>
              <div>
                <strong>Focus where it matters</strong>
                <p>
                  {o.high_risk_zones} zones meet the demonstration high-priority
                  threshold.
                </p>
              </div>
            </div>
            <button onClick={() => navigate("Explainable AI")}>
              Understand the drivers <ArrowRight size={17} />
            </button>
          </section>
          <Card className="next-action">
            <div className="next-icon">
              <FlaskConical size={20} />
            </div>
            <div>
              <strong>What could a cooler city look like?</strong>
              <p>Test your next intervention.</p>
            </div>
            <button
              aria-label="Open intervention simulator"
              onClick={() => navigate("Intervention simulator")}
            >
              <ArrowUpRight size={20} />
            </button>
          </Card>
        </div>
      </div>
      <div className="overview-bottom">
        <Card
          title="Priority zones"
          subtitle="Ranked by the configured hazard × exposure × vulnerability score"
          action={
            <button
              className="text-button"
              onClick={() => navigate("Heat risk")}
            >
              View all zones <ArrowRight size={14} />
            </button>
          }
        >
          <ZoneTable
            zones={o.priority_zones.slice(0, 5)}
            onSelect={(p: any) => {
              onSelect(p);
              navigate("Heat map");
            }}
          />
        </Card>
        <Card
          title="What's driving surface heat?"
          subtitle="Mean absolute SHAP contribution · °C"
          action={<Network size={18} color="#7c8a83" />}
        >
          <Importance data={o.importance.slice(0, 5)} />
          <div className="chart-note">
            Model associations, not proof of causation.
            <button onClick={() => navigate("Explainable AI")}>
              Explore XAI <ArrowUpRight size={12} />
            </button>
          </div>
        </Card>
      </div>
      <Notice>
        This workspace uses synthetic environmental and demographic data. Live
        imports are stored separately. Predictions and intervention estimates
        are for method exploration, not operational planning.
      </Notice>
    </>
  );
}
function ZoneTable({ zones, onSelect }: any) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>ANALYSIS ZONE</th>
            <th>SUHII</th>
            <th>POPULATION</th>
            <th>PRIORITY</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {zones.map((p: any, i: number) => (
            <tr key={p.id}>
              <td>
                <button className="zone-link" onClick={() => onSelect(p)}>
                  <span className="zone-number">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  {p.name}
                </button>
              </td>
              <td className="temperature">+{fmt(p.predicted_suhii)}°C</td>
              <td>{fmt(p.population / 1000)}k</td>
              <td>
                <Badge
                  tone={
                    p.risk_level === "High"
                      ? "red"
                      : p.risk_level === "Moderate"
                        ? "orange"
                        : "green"
                  }
                >
                  {p.risk_level}
                </Badge>
              </td>
              <td>
                <button
                  className="icon-button"
                  aria-label={"View " + p.name}
                  onClick={() => onSelect(p)}
                >
                  <ArrowUpRight size={15} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function Importance({ data, local = false }: any) {
  return (
    <div className="importance-chart">
      <ResponsiveContainer width="100%" height={218}>
        <BarChart
          data={data.map((d: any) => ({ ...d, name: label(d.feature) }))}
          layout="vertical"
          margin={{ left: 4, right: 24, top: 12, bottom: 0 }}
        >
          <CartesianGrid horizontal={false} stroke="#edf0eb" />
          <XAxis
            type="number"
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 10 }}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={115}
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 11, fill: "#66746c" }}
          />
          <Tooltip formatter={(v: any) => fmt(v, 3) + "°C"} />
          <Bar
            isAnimationActive={false}
            dataKey="importance"
            radius={[0, 3, 3, 0]}
            barSize={16}
          >
            {data.map((d: any, i: number) => (
              <Cell
                key={i}
                fill={
                  local && d.importance < 0
                    ? "#6f9bad"
                    : i === 0
                      ? "#27745c"
                      : "#9cbcad"
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
function ZoneDetails({ selected: p, navigate }: any) {
  return (
    <Card
      title={p.name}
      subtitle="Selected analysis zone"
      className="zone-detail"
    >
      <Badge tone={p.protected ? "orange" : "green"}>
        {p.protected ? "Protected land" : "Mixed urban area"}
      </Badge>
      <div className="zone-big">
        +{fmt(p.predicted_suhii)}
        <span>°C SUHII</span>
      </div>
      <p className="muted">
        Residual-calibrated range: {fmt(p.interval_low)} to{" "}
        {fmt(p.interval_high)}°C. Coverage is unvalidated.
      </p>
      <dl className="details-list">
        <div>
          <dt>Predicted surface temperature</dt>
          <dd>{fmt(p.predicted_lst)}°C</dd>
        </div>
        <div>
          <dt>Rural reference surface temperature</dt>
          <dd>{fmt(p.rural_reference)}°C</dd>
        </div>
        <div>
          <dt>Vegetation index (NDVI)</dt>
          <dd>{fmt(p.ndvi, 2)}</dd>
        </div>
        <div>
          <dt>Building density</dt>
          <dd>{fmt(p.building_density * 100, 0)}%</dd>
        </div>
        <div>
          <dt>Synthetic population</dt>
          <dd>{fmt(p.population, 0)}</dd>
        </div>
        <div>
          <dt>Risk score / 100</dt>
          <dd>{fmt(p.risk_score)}</dd>
        </div>
        <div>
          <dt>Spatial partition</dt>
          <dd>{p.partition}</dd>
        </div>
      </dl>
      {navigate && (
        <Button onClick={() => navigate("Intervention simulator")}>
          Test an intervention <ArrowRight size={15} />
        </Button>
      )}
    </Card>
  );
}
function Prediction({ city, data, overview, notify }: any) {
  const client = useQueryClient();
  const train = useMutation({
    mutationFn: () => api("/models/train", { city }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["overview", city] });
      client.invalidateQueries({ queryKey: ["map", city] });
      notify("Models retrained and spatial evaluation updated.");
    },
  });
  const m = overview.model;
  return (
    <>
      <div className="section-toolbar">
        <Notice>
          All metrics below are measured on held-out synthetic labels.
          Real-world validation is unavailable.
        </Notice>
        <Button onClick={() => train.mutate()} disabled={train.isPending}>
          <RefreshCw size={15} className={train.isPending ? "spin" : ""} />
          {train.isPending ? "Training…" : "Retrain models"}
        </Button>
      </div>
      {train.isError && <Notice error>{train.error.message}</Notice>}
      <div className="model-cards">
        {m.evaluations.map((v: any) => (
          <Card
            key={v.model}
            title={v.model}
            action={
              m.winner === v.model ? (
                <Badge>Selected</Badge>
              ) : (
                <Badge tone="neutral">Compared</Badge>
              )
            }
          >
            <div className="model-score">
              {fmt(v.test.r2, 3)}
              <span>R² on test zones</span>
            </div>
            <div className="model-stats">
              <div>
                <small>RMSE</small>
                <strong>{fmt(v.test.rmse, 3)}°C</strong>
              </div>
              <div>
                <small>MAE</small>
                <strong>{fmt(v.test.mae, 3)}°C</strong>
              </div>
              <div>
                <small>Validation RMSE</small>
                <strong>{fmt(v.validation.rmse, 3)}°C</strong>
              </div>
            </div>
          </Card>
        ))}
      </div>
      <div className="two-columns">
        <Card
          title="Observed label vs. prediction"
          subtitle="Spatial test partition only · synthetic SUHII"
        >
          <ResponsiveContainer width="100%" height={330}>
            <ScatterChart margin={{ top: 25, right: 30, bottom: 20, left: 15 }}>
              <CartesianGrid stroke="#e9eeea" />
              <XAxis
                type="number"
                dataKey="observed_suhii"
                name="Synthetic label"
                unit="°C"
              />
              <YAxis
                type="number"
                dataKey="predicted_suhii"
                name="Prediction"
                unit="°C"
              />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} />
              <ReferenceLine
                segment={[
                  { x: 0, y: 0 },
                  { x: 7, y: 7 },
                ]}
                stroke="#aaa"
                strokeDasharray="5 5"
              />
              <Scatter
                isAnimationActive={false}
                data={data.features
                  .filter((f: any) => f.properties.partition === "test")
                  .map((f: any) => f.properties)}
                fill="#377e68"
              />
            </ScatterChart>
          </ResponsiveContainer>
        </Card>
        <Card
          title="A spatially separated evaluation"
          subtitle="Model selection uses validation data, not the test set."
        >
          <div className="split-graphic">
            {["training", "validation", "buffer", "test"].map((s, i) => (
              <div
                key={s}
                className={"split s" + i}
                style={{ flex: m.split[s] }}
              >
                <strong>{m.split[s]}</strong>
                <span>{s}</span>
              </div>
            ))}
          </div>
          <div className="prose">
            <p>{m.split.method}</p>
            <p>
              <strong>Uncertainty:</strong> ±{fmt(m.interval, 2)}°C from the
              validation set's 90th-percentile absolute residual. This is an
              empirical band; real-world coverage is unknown.
            </p>
            <p>
              <strong>Historical trend:</strong> unavailable. The sample has one
              observation period; a temporal trend would be misleading.
            </p>
            <p>
              <strong>Model:</strong> {m.winner} selected by lowest validation
              RMSE. Target: urban surface temperature minus the configured rural
              surface-temperature reference.
            </p>
          </div>
        </Card>
      </div>
    </>
  );
}
function Explain({ city, data, selected, onSelect, overview }: any) {
  const explanation = useQuery({
    queryKey: ["explain", city, selected.id],
    queryFn: () => api("/xai/explain", { city, zone_id: selected.id }),
  });
  return (
    <>
      <div className="section-toolbar">
        <p className="muted">
          Actual TreeSHAP values from the trained {overview.model.winner} model.
        </p>
        <ZonePicker data={data} selected={selected} onSelect={onSelect} />
      </div>
      <div className="two-columns">
        <Card
          title="Global feature importance"
          subtitle="Mean |SHAP| across the analysis grid · °C"
        >
          <Importance data={overview.importance} />
        </Card>
        <Card
          title="Why this zone?"
          subtitle={selected.name + " · Local contribution to predicted SUHII"}
        >
          {explanation.data ? (
            <>
              <Importance
                local
                data={Object.entries(explanation.data.contributions)
                  .map(([feature, importance]) => ({ feature, importance }))
                  .sort(
                    (a: any, b: any) =>
                      Math.abs(b.importance) - Math.abs(a.importance),
                  )
                  .slice(0, 7)}
              />
              <div className="equation">
                Base {fmt(explanation.data.base_value, 2)}°C + contributions ={" "}
                <strong>{fmt(explanation.data.prediction, 2)}°C</strong>
              </div>
            </>
          ) : explanation.isError ? (
            <Notice error>{explanation.error.message}</Notice>
          ) : (
            <Pending />
          )}
        </Card>
      </div>
      <Card
        title="How vegetation's contribution varies"
        subtitle="Spatial SHAP: red increases, blue decreases the model prediction"
      >
        <HeatMap
          data={data}
          selected={selected.id}
          onSelect={onSelect}
          layer="shap_ndvi"
          onLayer={() => {}}
        />
      </Card>
      <Notice>
        SHAP explains associations learned by this model. Its values are never
        used as cooling coefficients in the intervention simulator.
      </Notice>
    </>
  );
}
function Risk({ city, data, selected, onSelect }: any) {
  const [weights, setWeights] = useState([1, 1, 1]),
    [query, setQuery] = useState("");
  const run = useMutation({
    mutationFn: () =>
      api("/risk/analyze", {
        city,
        hazard_weight: weights[0],
        exposure_weight: weights[1],
        vulnerability_weight: weights[2],
      }),
  });
  const scores = new globalThis.Map(
    (run.data?.zones || []).map((z: any) => [z.zone_id, z]),
  );
  const zones = data.features
    .map((f: any) => ({
      ...f.properties,
      ...((scores.get(f.properties.id) as object) || {}),
    }))
    .filter((p: any) => p.name.toLowerCase().includes(query.toLowerCase()))
    .sort((a: any, b: any) => b.risk_score - a.risk_score);
  return (
    <>
      <div className="two-columns risk-layout">
        <Card
          title="Make priorities explicit"
          subtitle="Configure the exponents in the risk framework."
        >
          <div className="equation">
            Risk = Hazard<sup>wH</sup> × Exposure<sup>wE</sup> × Vulnerability
            <sup>wV</sup>
          </div>
          <div className="form-body">
            {["Hazard", "Exposure", "Vulnerability"].map((name, i) => (
              <label className="slider-label" key={name}>
                <span>
                  {name} exponent <strong>{weights[i].toFixed(1)}</strong>
                </span>
                <input
                  aria-label={name + " weight"}
                  type="range"
                  min="0.1"
                  max="3"
                  step="0.1"
                  value={weights[i]}
                  onChange={(e) =>
                    setWeights(
                      weights.map((w, j) =>
                        i === j ? Number(e.target.value) : w,
                      ),
                    )
                  }
                />
              </label>
            ))}
            <Button onClick={() => run.mutate()} disabled={run.isPending}>
              {run.isPending ? "Calculating…" : "Recalculate priorities"}
            </Button>
            {run.isError && <Notice error>{run.error.message}</Notice>}
          </div>
        </Card>
        <Card
          title="What the score can tell you"
          subtitle="Transparent inputs, visible gaps"
        >
          <div className="prose">
            <p>
              <strong>Hazard:</strong> predicted SUHII divided by 8°C.
            </p>
            <p>
              <strong>Exposure:</strong> population density divided by 25,000
              people/km².
            </p>
            <p>
              <strong>Vulnerability:</strong> synthetic elderly share divided by
              25%. Population density is not used as vulnerability.
            </p>
            <p>
              Each component is clipped to [0, 1], raised to its configured
              exponent, multiplied, then scaled to 100. High ≥20; moderate ≥8.
            </p>
            <Notice>
              Socioeconomic conditions, health data, and access to cooling are
              unavailable. This is a screening proxy, not a health-risk
              forecast.
            </Notice>
          </div>
        </Card>
      </div>
      <Card
        title="Zone priorities"
        subtitle={`${zones.length} zones · ${run.data ? "Recalculated" : "Default"} framework`}
        action={
          <div className="search-box">
            <Search size={15} />
            <input
              placeholder="Find a sector…"
              aria-label="Search zones"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
        }
      >
        <ZoneTable zones={zones.slice(0, 40)} onSelect={onSelect} />
      </Card>
      <div className="selected-summary">
        Selected: {selected.name} · Risk score{" "}
        {fmt(
          (scores.get(selected.id) as any)?.risk_score ?? selected.risk_score,
        )}
      </div>
    </>
  );
}
function Simulator({ city, data, selected, onSelect, notify }: any) {
  const [coverage, setCoverage] = useState<Record<string, number>>({
      trees: 5,
      cool_roofs: 10,
    }),
    [name, setName] = useState("Greener streets"),
    [water, setWater] = useState(1000);
  const client = useQueryClient();
  const history = useQuery({
    queryKey: ["scenarios", city],
    queryFn: () => api("/simulation/results?city=" + city),
  });
  const run = useMutation({
    mutationFn: () =>
      api("/simulation/run", {
        city,
        zone_id: selected.id,
        name,
        coverage,
        water_limit: water,
      }),
    onSuccess: (r) => {
      client.invalidateQueries({ queryKey: ["scenarios", city] });
      notify(
        r.feasible
          ? "Scenario calculated and saved."
          : "Scenario saved with constraint violations.",
      );
    },
  });
  return (
    <>
      <div className="section-toolbar">
        <Notice>
          Hypothetical surface-cooling estimates. Coefficients are uncalibrated;
          ±40% is a sensitivity range.
        </Notice>
        <ZonePicker
          data={data}
          selected={selected}
          onSelect={(p: any) => {
            onSelect(p);
            run.reset();
          }}
        />
      </div>
      <div className="sim-layout">
        <Card
          title="Design your scenario"
          subtitle="Coverage is % of total zone area."
        >
          <div className="form-body">
            <label>
              Scenario name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={80}
              />
            </label>
            <div className="constraint-summary">
              <span>
                Land <b>{fmt(selected.available_land_pct, 0)}%</b>
              </span>
              <span>
                Roofs <b>{fmt(selected.roof_pct, 0)}%</b>
              </span>
              <span>
                Roads <b>{fmt(selected.road_pct, 0)}%</b>
              </span>
            </div>
            {Object.entries(interventionNames).map(([key, title]) => (
              <label className="slider-label compact" key={key}>
                <span>
                  {title}
                  <strong>{coverage[key] || 0}%</strong>
                </span>
                <input
                  type="range"
                  aria-label={title + " coverage"}
                  min="0"
                  max="60"
                  step="5"
                  value={coverage[key] || 0}
                  onChange={(e) => {
                    setCoverage({ ...coverage, [key]: Number(e.target.value) });
                    run.reset();
                  }}
                />
              </label>
            ))}
            <label>
              Available water (m³/day)
              <input
                type="number"
                min="0"
                value={water}
                onChange={(e) => {
                  setWater(Number(e.target.value));
                  run.reset();
                }}
              />
            </label>
            <Button
              onClick={() => run.mutate()}
              disabled={run.isPending || !name.trim()}
            >
              <FlaskConical size={16} />
              {run.isPending ? "Simulating…" : "Run & save scenario"}
            </Button>
          </div>
        </Card>
        <div className="stack">
          <Card title="Before & after" subtitle={selected.name}>
            {run.isError ? (
              <Notice error>{run.error.message}</Notice>
            ) : run.isPending ? (
              <Pending />
            ) : run.data ? (
              run.data.feasible ? (
                <div className="scenario-result">
                  <Badge>Feasible under supplied constraints</Badge>
                  <div className="comparison">
                    <div>
                      <span>Current SUHII</span>
                      <strong>+{fmt(run.data.before_suhii)}°C</strong>
                    </div>
                    <ArrowRight />
                    <div className="after">
                      <span>Scenario SUHII</span>
                      <strong>{fmt(run.data.after_suhii)}°C</strong>
                    </div>
                  </div>
                  <div className="cooling-impact">
                    <ArrowDown size={22} />
                    <strong>{fmt(run.data.estimated_cooling, 2)}°C</strong>
                    <span>hypothetical surface cooling</span>
                  </div>
                  <p>
                    Sensitivity range:{" "}
                    {run.data.sensitivity_range
                      .map((n: number) => fmt(n, 2))
                      .join("–")}
                    °C
                  </p>
                  <p>
                    Water requirement: {fmt(run.data.water_m3_day, 0)} m³/day
                  </p>
                </div>
              ) : (
                <div className="form-body">
                  <Notice error>
                    Scenario is infeasible. No cooling result is claimed.
                  </Notice>
                  {run.data.violations.map((v: string) => (
                    <p key={v}>{v}</p>
                  ))}
                </div>
              )
            ) : (
              <div className="empty">
                <TreePine size={36} />
                <h3>A small change. A different possibility.</h3>
                <p>
                  Choose coverage, then run your scenario
                  <br />
                  to calculate effects and check feasibility.
                </p>
              </div>
            )}
          </Card>
          <Card
            title="Scenario comparison"
            subtitle="Saved runs from this city"
          >
            {history.data?.length ? (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>SCENARIO</th>
                      <th>COOLING</th>
                      <th>STATUS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.data.slice(0, 8).map((s: any) => (
                      <tr key={s.id}>
                        <td>
                          {s.name}
                          <small className="block muted">{s.zone_id}</small>
                        </td>
                        <td>
                          {s.feasible
                            ? fmt(s.estimated_cooling, 2) + "°C"
                            : "—"}
                        </td>
                        <td>
                          <Badge tone={s.feasible ? "green" : "red"}>
                            {s.feasible ? "Feasible" : "Infeasible"}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty small">
                Your saved scenarios will appear here.
              </div>
            )}
          </Card>
          <Notice>
            Ground area is shared by trees, parks, vegetation, corridors, and
            water. Roof treatments are mutually exclusive. Protected zones
            exclude ground interventions.
          </Notice>
        </div>
      </div>
    </>
  );
}
function Optimizer({ city, overview, notify }: any) {
  const [water, setWater] = useState(1000),
    [vegetation, setVegetation] = useState(40),
    [land, setLand] = useState(100),
    [minimum, setMinimum] = useState(0);
  const run = useMutation({
    mutationFn: () =>
      api("/optimization/run", {
        city,
        water_limit: water,
        max_vegetation_pct: vegetation,
        land_limit_pct: land,
        min_cooling: minimum,
      }),
    onSuccess: () => notify("Optimization run saved."),
  });
  return (
    <>
      <div className="sim-layout">
        <Card
          title="Set the boundaries"
          subtitle="OR-Tools CP-SAT · no budget objective"
        >
          <div className="form-body">
            <label>
              Total available water (m³/day)
              <input
                type="number"
                min="0"
                value={water}
                onChange={(e) => {
                  setWater(+e.target.value);
                  run.reset();
                }}
              />
            </label>
            <label className="slider-label">
              <span>
                Maximum added vegetation<strong>{vegetation}%</strong>
              </span>
              <input
                type="range"
                min="0"
                max="60"
                value={vegetation}
                onChange={(e) => {
                  setVegetation(+e.target.value);
                  run.reset();
                }}
              />
            </label>
            <label className="slider-label">
              <span>
                Use of available ground area<strong>{land}%</strong>
              </span>
              <input
                type="range"
                min="0"
                max="100"
                value={land}
                onChange={(e) => {
                  setLand(+e.target.value);
                  run.reset();
                }}
              />
            </label>
            <label>
              Minimum mean surface cooling (°C)
              <input
                type="number"
                min="0"
                max="4"
                step=".1"
                value={minimum}
                onChange={(e) => {
                  setMinimum(+e.target.value);
                  run.reset();
                }}
              />
            </label>
            <p className="muted">
              Analyzing the five highest-priority zones. The objective weights
              hypothetical cooling by heat, population, and elderly share.
            </p>
            <div className="mini-zone-list">
              {overview.priority_zones.slice(0, 5).map((p: any) => (
                <span key={p.id}>
                  <MapPin size={12} />
                  {p.name}
                </span>
              ))}
            </div>
            <Button onClick={() => run.mutate()} disabled={run.isPending}>
              <Target size={16} />
              {run.isPending
                ? "Finding a feasible plan…"
                : "Optimize interventions"}
            </Button>
          </div>
        </Card>
        <div className="stack">
          <Card
            title="Your intervention plan"
            subtitle="Feasible solutions backed by explicit constraints"
          >
            {run.isPending ? (
              <Pending />
            ) : run.isError ? (
              <Notice error>{run.error.message}</Notice>
            ) : run.data ? (
              run.data.feasible ? (
                <>
                  <div className="optimization-head">
                    <Badge>
                      <Check size={12} />
                      {run.data.status}
                    </Badge>
                    <span>
                      {fmt(run.data.water_used, 0)} /{" "}
                      {fmt(run.data.water_available, 0)} m³ water/day
                    </span>
                  </div>
                  <div className="plan-metrics">
                    <div>
                      <strong>{fmt(run.data.mean_cooling, 2)}°C</strong>
                      <span>Mean hypothetical cooling</span>
                    </div>
                    <div>
                      <strong>
                        {fmt(run.data.population_in_selected_zones / 1000)}k
                      </strong>
                      <span>Population in selected zones</span>
                    </div>
                  </div>
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>ZONE</th>
                          <th>INTERVENTIONS · COVERAGE</th>
                          <th>COOLING</th>
                        </tr>
                      </thead>
                      <tbody>
                        {run.data.selections.map((s: any) => (
                          <tr key={s.zone_id}>
                            <td>{s.zone_name}</td>
                            <td>
                              {Object.entries(s.coverage).map(([k, v]) => (
                                <span className="block" key={k}>
                                  {interventionNames[k]} · {String(v)}%
                                </span>
                              ))}
                            </td>
                            <td>{fmt(s.estimated_cooling, 2)}°C</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="prose">
                    <p>{run.data.explanation}</p>
                  </div>
                </>
              ) : (
                <div className="form-body">
                  <Notice error>
                    No feasible plan found: {run.data.status}
                  </Notice>
                  {run.data.violations.map((s: string) => (
                    <p key={s}>{s}</p>
                  ))}
                </div>
              )
            ) : (
              <div className="empty">
                <Target size={40} />
                <h3>The right combination, within reach.</h3>
                <p>
                  Set practical limits and find a feasible
                  <br />
                  combination of cooling interventions.
                </p>
              </div>
            )}
          </Card>
          {run.data?.alternative?.feasible && (
            <Card
              title="An alternative with less water"
              subtitle="Same constraints; half the daily water allowance"
            >
              <div className="prose">
                <p>
                  <strong>{fmt(run.data.alternative.mean_cooling, 2)}°C</strong>{" "}
                  mean hypothetical cooling with{" "}
                  <strong>
                    {fmt(run.data.alternative.water_used, 0)} m³/day
                  </strong>
                  .
                </p>
              </div>
            </Card>
          )}
          <Notice>
            Population in selected zones is not “people protected.” The
            objective is a planning proxy. All intervention effects require
            local validation.
          </Notice>
        </div>
      </div>
    </>
  );
}
function Assistant({ city, data, selected, onSelect }: any) {
  const [message, setMessage] = useState(""),
    [provider, setProvider] = useState("auto"),
    [messages, setMessages] = useState<any[]>([]);
  const send = useMutation({
    mutationFn: (question: string) =>
      api("/ai/chat", {
        city,
        zone_id: selected.id,
        message: question,
        provider,
      }),
    onSuccess: (r) => setMessages((m) => [...m, { role: "assistant", ...r }]),
  });
  function submit(q: string) {
    if (!q.trim() || send.isPending) return;
    setMessages((m) => [...m, { role: "user", text: q }]);
    setMessage("");
    send.mutate(q);
  }
  return (
    <>
      <div className="section-toolbar">
        <ZonePicker data={data} selected={selected} onSelect={onSelect} />
        <select
          className="select"
          aria-label="AI provider"
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
        >
          <option value="auto">Auto · Groq → Gemini</option>
          <option value="groq">Groq</option>
          <option value="gemini">Gemini</option>
          <option value="local">Local evidence summary</option>
        </select>
      </div>
      <div className="chat-layout">
        <Card className="chat-card">
          <div className="chat-messages">
            {!messages.length && (
              <div className="chat-welcome">
                <div className="assistant-mark">
                  <Sparkles size={30} />
                </div>
                <h2>
                  Good questions lead
                  <br />
                  to cooler possibilities.
                </h2>
                <p>
                  Explore the evidence for {selected.name}.<br />
                  Your assistant receives actual backend results.
                </p>
                <div className="suggestions">
                  {[
                    "Why is this area hotter?",
                    "Which interventions are feasible?",
                    "Explain the optimization and its limitations.",
                  ].map((q) => (
                    <button key={q} onClick={() => submit(q)}>
                      {q}
                      <ArrowUpRight size={14} />
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <div className={"message " + m.role} key={i}>
                {m.role === "user" ? (
                  m.text
                ) : (
                  <>
                    <div className="message-provider">
                      <Sparkles size={14} />
                      {m.provider}
                      <Badge tone="neutral">
                        {m.fallback ? "Template fallback" : "Provider response"}
                      </Badge>
                    </div>
                    <p>{m.summary}</p>
                    {m.findings.map((f: any, j: number) => (
                      <p key={j}>
                        {f.statement}{" "}
                        <small className="citation">
                          {f.fact_ids.join(" · ")}
                        </small>
                      </p>
                    ))}
                    <div className="action-tags">
                      {m.actions.map((a: string) => (
                        <Badge key={a}>{interventionNames[a]}</Badge>
                      ))}
                    </div>
                    <details>
                      <summary>Evidence & limitations</summary>
                      <p>
                        Predicted SUHII: {fmt(m.facts.prediction.suhii_c, 2)}°C
                        · synthetic.
                      </p>
                      {m.limitations.map((l: string) => (
                        <p key={l}>{l}</p>
                      ))}
                      {m.failures.map((f: any) => (
                        <p key={f.provider}>
                          {f.provider}: {f.reason}
                        </p>
                      ))}
                    </details>
                  </>
                )}
              </div>
            ))}
            {send.isPending && <Pending />}
            {send.isError && <Notice error>{send.error.message}</Notice>}
          </div>
          <form
            className="chat-input"
            onSubmit={(e) => {
              e.preventDefault();
              submit(message);
            }}
          >
            <input
              aria-label="Ask about this zone"
              placeholder="Ask about this zone, a scenario, or an intervention…"
              value={message}
              maxLength={2000}
              onChange={(e) => setMessage(e.target.value)}
            />
            <Button
              aria-label="Send message"
              disabled={!message.trim() || send.isPending}
            >
              <Send size={18} />
            </Button>
          </form>
          <div className="chat-disclaimer">
            Evidence-grounded support. Verify recommendations before making
            planning decisions.
          </div>
        </Card>
        <ZoneDetails selected={selected} />
      </div>
    </>
  );
}
function Reports({ city, overview, status, notify }: any) {
  const [report, setReport] = useState<any>();
  const create = useMutation({
    mutationFn: () => api("/reports/generate", { city }),
    onSuccess: (r) => {
      setReport(r);
      notify("Report generated from current analysis.");
    },
  });
  const save = async (url: string, name: string) => {
    try {
      await download(url, name);
    } catch (e: any) {
      notify(e.message);
    }
  };
  return (
    <>
      <div className="report-banner">
        <div>
          <div className="eyebrow">FROM ANALYSIS TO ACTION</div>
          <h2>
            Your city's evidence,
            <br />
            ready to share.
          </h2>
          <p>
            A reproducible snapshot of model results, scenarios,
            <br />
            constraints, sources, and limitations.
          </p>
          <Button onClick={() => create.mutate()} disabled={create.isPending}>
            <FileText size={16} />
            {create.isPending ? "Generating…" : "Generate analysis report"}
          </Button>
        </div>
        <div className="report-illustration">
          <FileText size={85} strokeWidth={1} />
          <span>
            HEATWISE
            <br />
            <strong>{city}</strong>
            <small>URBAN HEAT ANALYSIS</small>
          </span>
          <Badge>SYNTHETIC DEMONSTRATION</Badge>
        </div>
      </div>
      {create.isError && <Notice error>{create.error.message}</Notice>}
      {report && (
        <div className="download-grid">
          {[
            [
              "markdown_url",
              "Readable report",
              "Markdown · methods & results",
              "md",
            ],
            ["csv_url", "Zone-level data", "CSV · predictions & risk", "csv"],
            [
              "download_url",
              "Complete analysis",
              "JSON · all evidence",
              "json",
            ],
          ].map(([key, title, desc, ext]) => (
            <Card key={key}>
              <div className="download-card">
                <FileText />
                <h3>{title}</h3>
                <p>{desc}</p>
                <Button
                  variant="outline"
                  onClick={() => save(report[key], "heatwise-report." + ext)}
                >
                  <ArrowDownToLine size={15} />
                  Download {ext.toUpperCase()}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
      <div className="two-columns">
        <Card
          title="Methodology & provenance"
          subtitle="Reproduce the result, understand its limits"
        >
          <div className="prose">
            <p>
              <strong>Surface heat:</strong> SUHII = urban land surface
              temperature − rural reference land surface temperature. Current
              reference: {overview.metadata.rural_reference_c}°C, synthetic.
            </p>
            <p>
              <strong>Dataset:</strong> seeded synthetic grid,{" "}
              {overview.zone_count} cells. The acquisition date is a
              demonstration label. Live imports never silently replace the
              sample.
            </p>
            <p>
              <strong>Prediction:</strong> three tree ensembles; spatial
              train/validation/buffer/test split. Actual TreeSHAP explanations.
            </p>
            <p>
              <strong>Interventions:</strong> independent hypothetical
              coefficients. No conversion of SHAP values into cooling estimates.
            </p>
            <p>
              <strong>Optimization:</strong> CP-SAT with 5% coverage increments,
              water, surface capacity, compatibility, protection, and vegetation
              constraints. No cost objective.
            </p>
          </div>
        </Card>
        <Card
          title="Connection status"
          subtitle="Configuration is not proof of successful access"
        >
          <div className="prose">
            <div className="source-row">
              <span>Database</span>
              <Badge tone="neutral">{status?.database || "Loading"}</Badge>
            </div>
            {["groq", "gemini"].map((p) => (
              <div className="source-row" key={p}>
                <span>{p === "groq" ? "Groq" : "Google Gemini"}</span>
                <Badge
                  tone={status?.providers[p].configured ? "green" : "orange"}
                >
                  {status?.providers[p].configured
                    ? "Configured · unverified"
                    : "Needs key & model"}
                </Badge>
              </div>
            ))}
            <div className="source-row">
              <span>Google Earth Engine</span>
              <Badge
                tone={status?.earth_engine_configured ? "green" : "orange"}
              >
                {status?.earth_engine_configured
                  ? "Configured · unverified"
                  : "Needs credentials"}
              </Badge>
            </div>
            <Notice>
              Server environment: GROQ_API_KEY + GROQ_MODEL, GEMINI_API_KEY +
              GEMINI_MODEL, EARTH_ENGINE_PROJECT + Google application
              credentials. Models are validated through the provider API before
              use.
            </Notice>
          </div>
        </Card>
      </div>
    </>
  );
}
function DataDialog({ city, close, notify }: any) {
  const client = useQueryClient();
  const [source, setSource] = useState("weather"),
    [lat, setLat] = useState(""),
    [lon, setLon] = useState(""),
    [start, setStart] = useState(""),
    [end, setEnd] = useState(""),
    [boundary, setBoundary] = useState(""),
    [rural, setRural] = useState(33),
    [satelliteProduct, setSatelliteProduct] = useState("landsat");
  const status = useQuery({
    queryKey: ["status"],
    queryFn: () => api("/data/status"),
  });
  const ingest = useMutation({
    mutationFn: () => {
      const body: any = {
        city,
        source,
        rural_reference: rural,
        satellite_product: satelliteProduct,
      };
      if (lat || lon) {
        body.latitude = Number(lat);
        body.longitude = Number(lon);
      }
      if (start || end) {
        body.start_date = start;
        body.end_date = end;
      }
      if (boundary.trim()) body.boundary = JSON.parse(boundary);
      return api("/data/ingest", body);
    },
    onSuccess: () => {
      client.invalidateQueries();
      notify("Ingestion completed. Source and provenance saved.");
    },
  });
  return (
    <div className="modal-backdrop">
      <div className="modal">
        <button
          className="modal-close"
          aria-label="Close data sources"
          onClick={close}
        >
          <X />
        </button>
        <div className="eyebrow">DATA WORKSPACE</div>
        <h2>Know where your data comes from.</h2>
        <p>Live evidence stays separate from synthetic predictions.</p>
        <div className="data-form">
          <label>
            Data source
            <select
              value={source}
              onChange={(e) => {
                setSource(e.target.value);
                ingest.reset();
              }}
            >
              <option value="weather">
                Open-Meteo · current / historical weather
              </option>
              <option value="osm">OpenStreetMap · geographical features</option>
              <option value="stac">
                Sentinel-2 · public satellite catalog
              </option>
              <option value="sentinel_indices">
                Sentinel-2 · process live optical indices
              </option>
              <option value="earth_engine">
                Earth Engine · Landsat LST & indices
              </option>
              <option value="worldpop">
                WorldPop · population dataset catalog
              </option>
              <option value="openaq">
                OpenAQ · optional monitoring stations
              </option>
              <option value="sample">Rebuild synthetic sample & retrain</option>
            </select>
          </label>
          {source === "earth_engine" && (
            <label>
              Satellite product
              <select
                aria-label="Satellite product"
                value={satelliteProduct}
                onChange={(e) => setSatelliteProduct(e.target.value)}
              >
                <option value="landsat">Landsat 8/9 · LST and indices</option>
                <option value="sentinel">Sentinel-2 · optical indices</option>
                <option value="modis">MODIS · eight-day daytime LST</option>
                <option value="worldcover">
                  ESA WorldCover · 2021 land cover
                </option>
                <option value="srtm">NASA SRTM · elevation</option>
              </select>
            </label>
          )}
          <div className="two-columns">
            <label>
              Latitude (optional)
              <input
                type="number"
                step="any"
                value={lat}
                placeholder="City center"
                onChange={(e) => setLat(e.target.value)}
              />
            </label>
            <label>
              Longitude (optional)
              <input
                type="number"
                step="any"
                value={lon}
                placeholder="City center"
                onChange={(e) => setLon(e.target.value)}
              />
            </label>
          </div>
          <div className="two-columns">
            <label>
              Start date (optional)
              <input
                type="date"
                value={start}
                onChange={(e) => setStart(e.target.value)}
              />
            </label>
            <label>
              End date (optional)
              <input
                type="date"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
              />
            </label>
          </div>
          {(source === "sample" || source === "earth_engine") && (
            <>
              <label>
                GeoJSON Polygon{" "}
                {source === "earth_engine" ? "(required)" : "(optional)"}
                <textarea
                  value={boundary}
                  onChange={(e) => setBoundary(e.target.value)}
                  rows={3}
                  placeholder='{"type":"Polygon","coordinates":[…]}'
                />
              </label>
              {source === "sample" && (
                <label>
                  Synthetic rural reference LST (°C)
                  <input
                    type="number"
                    value={rural}
                    onChange={(e) => setRural(+e.target.value)}
                  />
                </label>
              )}
            </>
          )}
          <Button
            onClick={() => ingest.mutate()}
            disabled={ingest.isPending || Boolean(lat) !== Boolean(lon)}
          >
            <Database size={16} />
            {ingest.isPending
              ? "Retrieving and validating…"
              : "Ingest selected source"}
          </Button>
          {ingest.isError && <Notice error>{ingest.error.message}</Notice>}
          {ingest.data && (
            <div className="ingestion-result">
              <Badge>
                <CheckCircle2 size={13} />
                Ingestion succeeded
              </Badge>
              <p>
                {ingest.data.source || ingest.data.metadata?.source} ·{" "}
                {ingest.data.synthetic === false ||
                ingest.data.metadata?.synthetic === false
                  ? "Live source"
                  : "Synthetic sample"}
              </p>
              <pre>
                {JSON.stringify(
                  ingest.data.data?.current ||
                    ingest.data.metadata || {
                      zones: ingest.data.zones,
                      dataset_count: ingest.data.datasets?.length,
                    },
                  null,
                  2,
                )}
              </pre>
              <details>
                <summary>Inspect retrieved evidence</summary>
                <pre>
                  {JSON.stringify(ingest.data, null, 2).slice(0, 18000)}
                </pre>
              </details>
            </div>
          )}
        </div>
        <h3 className="catalog-title">Satellite & environmental coverage</h3>
        {status.data?.catalog.map((d: any) => (
          <div className="source-row" key={d.id}>
            <div>
              {d.id}
              <small className="block muted">{d.resolution}</small>
            </div>
            <span className="muted">{d.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
