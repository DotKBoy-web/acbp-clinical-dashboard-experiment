import React, { useEffect, useMemo, useState, useCallback } from "react";
import {
  Activity,
  BarChart3,
  CheckCircle2,
  Database,
  Gauge,
  PlayCircle,
  RefreshCcw,
  ShieldCheck,
  Sparkles,
  Table2,
  Zap,
  AlertTriangle,
  Clock,
  Hash,
  Target,
  XCircle,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import Button from "./components/ui/button";
import Card, { CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "./components/ui/card";
import "./App.css";

// ============================================================================
// CONSTANTS
// ============================================================================

const STATIC_SUMMARY = {
  liveMeanMs: 416.41,
  acbpMeanMs: 211.97,
  liveP95Ms: 467.63,
  acbpP95Ms: 249.62,
  bufferRatio: 8.681,
  bufferReductionPct: 88.48,
  pairedComparisons: 48,
  hashMatchRate: "100%",
};

const metricLabels = { census: "Census", discharge: "Discharge", occupancy: "Occupancy" };
const metricIcons = { census: "🏥", discharge: "🚪", occupancy: "📊" };
const hitOptions = [3, 5, 10, 20, 50];

const latencySeries = Array.from({ length: 24 }, (_, i) => {
  const wiggle = Math.sin(i / 2) * 10 + (i % 5) * 3;
  return { iteration: i + 1, live: Math.round(416 + wiggle + (i % 3) * 8), acbp: Math.round(212 + wiggle / 2 + (i % 4) * 5) };
});

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function mean(values) {
  if (!values || values.length === 0) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function buildCompareChart(runs) {
  return runs.filter((r) => r.ok).map((r) => ({ run: `#${r.id}`, live: Number(r.liveMs), acbp: Number(r.acbpMs) })).filter((r) => Number.isFinite(r.live) && Number.isFinite(r.acbp));
}

// ============================================================================
// SMALL COMPONENTS
// ============================================================================

function StatusDot({ status }) {
  const config = { connected: { className: "connected", label: "Connected" }, error: { className: "disconnected", label: "Error" }, checking: { className: "checking", label: "Checking..." } };
  const c = config[status] || config.checking;
  return <span className="status-indicator"><span className={`status-dot ${c.className}`} /><span className="text-[11px] font-medium text-slate-300">{c.label}</span></span>;
}

function SmallBadge({ children, tone = "slate", pulse = false }) {
  const tones = { slate: "bg-slate-100 text-slate-700 border-slate-200", green: "bg-emerald-100 text-emerald-700 border-emerald-200", red: "bg-rose-100 text-rose-700 border-rose-200", blue: "bg-sky-100 text-sky-700 border-sky-200", amber: "bg-amber-100 text-amber-700 border-amber-200", purple: "bg-violet-100 text-violet-700 border-violet-200" };
  return <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${tones[tone] || tones.slate} ${pulse ? "animate-pulse-slow" : ""}`}>{children}</span>;
}

function StatCard({ icon: Icon, label, value, sub, tone = "slate" }) {
  const tones = { slate: "from-slate-50 to-white border-slate-200", green: "from-emerald-50 to-white border-emerald-200", red: "from-rose-50 to-white border-rose-200", blue: "from-sky-50 to-white border-sky-200", amber: "from-amber-50 to-white border-amber-200", purple: "from-violet-50 to-white border-violet-200" };
  const iconBgs = { slate: "bg-slate-100 text-slate-600", green: "bg-emerald-100 text-emerald-600", red: "bg-rose-100 text-rose-600", blue: "bg-sky-100 text-sky-600", amber: "bg-amber-100 text-amber-600", purple: "bg-violet-100 text-violet-600" };
  return <div className={`rounded-2xl border bg-gradient-to-br p-3 shadow-sm hover-lift ${tones[tone] || tones.slate}`}><div className="flex items-start justify-between gap-2"><div className="min-w-0 flex-1"><p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</p><p className="mt-0.5 truncate text-xl font-bold text-slate-900 tabular-nums">{value}</p>{sub && <p className="mt-0.5 truncate text-[11px] text-slate-500">{sub}</p>}</div><div className={`shrink-0 rounded-xl p-2 ${iconBgs[tone] || iconBgs.slate}`}><Icon className="h-4 w-4" /></div></div></div>;
}

function ProgressBar({ value, max = 100 }) {
  const pct = Math.min(Math.max((value / max) * 100, 0), 100);
  return <div className="w-full px-4 pb-2"><div className="flex justify-between text-[10px] text-slate-500 mb-1"><span>Progress</span><span>{pct.toFixed(0)}%</span></div><div className="h-2 w-full overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-emerald-600 transition-all duration-300" style={{ width: `${pct}%` }} /></div></div>;
}

function SpeedupVisual({ speedup }) {
  if (speedup === "—" || !speedup) return null;
  const val = parseFloat(speedup);
  const bars = Math.min(Math.round(val), 5);
  const color = val >= 2 ? "bg-emerald-500" : val >= 1.5 ? "bg-sky-500" : "bg-amber-500";
  return <div className="flex items-center gap-1">{Array.from({ length: 5 }).map((_, i) => <div key={i} className={`h-3 w-1.5 rounded-full ${i < bars ? color : "bg-slate-200"}`} />)}<span className="ml-1 text-xs font-bold text-slate-700">{speedup}x</span></div>;
}

// ============================================================================
// PANEL COMPONENTS
// ============================================================================

function SemanticPanel({ selectedSemantic, queryResult, path, selectedMetric }) {
  if (!selectedSemantic) return <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50 p-8 text-center"><Database className="h-8 w-8 text-slate-300" /><p className="text-sm text-slate-500">Semantic catalog not loaded.</p></div>;
  const resolution = path === "live" ? selectedSemantic.liveResolution : selectedSemantic.acbpResolution;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2"><SmallBadge tone="blue"><Sparkles className="h-3 w-3" /> Semantic</SmallBadge><SmallBadge tone={path === "acbp" ? "green" : "red"} pulse>{path === "acbp" ? "⚡ ACBP" : "🔴 Live SQL"}</SmallBadge><SmallBadge tone="purple">{metricIcons[selectedMetric]} {metricLabels[selectedMetric]}</SmallBadge></div>
      <div className="rounded-xl bg-white p-3 shadow-sm"><p className="text-[10px] font-bold uppercase tracking-wider text-sky-700">Business Metric</p><p className="mt-0.5 text-sm font-semibold">{selectedSemantic.label}</p><p className="mt-0.5 text-[11px] text-slate-500">Key: <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px]">{selectedMetric}</code></p></div>
      <div className="grid grid-cols-2 gap-2"><div className="rounded-xl bg-white p-3 shadow-sm"><p className="text-[10px] font-bold uppercase tracking-wider text-sky-700">📊 Power BI</p><p className="mt-0.5 text-xs font-medium">{selectedSemantic.powerbiObject}</p></div><div className="rounded-xl bg-white p-3 shadow-sm"><p className="text-[10px] font-bold uppercase tracking-wider text-sky-700">🔷 SAP / WebI</p><p className="mt-0.5 text-xs font-medium">{selectedSemantic.sapObject}</p></div></div>
      <div className="rounded-xl bg-white p-3 shadow-sm"><p className="text-[10px] font-bold uppercase tracking-wider text-sky-700">🎯 Resolution</p><p className="mt-0.5 text-xs leading-relaxed text-slate-600">{queryResult?.resolution || resolution || "Waiting..."}</p></div>
      <div className="rounded-xl bg-white p-3 shadow-sm"><p className="text-[10px] font-bold uppercase tracking-wider text-sky-700">📄 SQL File</p><p className="mt-0.5 truncate font-mono text-[11px]">{queryResult?.execution?.sqlFile || "Pending..."}</p></div>
    </div>
  );
}

function RowsPreview({ rows }) {
  if (!rows || rows.length === 0) return <div className="flex flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50 p-6"><Table2 className="h-6 w-6 text-slate-300" /><p className="text-xs text-slate-500">No rows returned.</p></div>;
  const columns = Object.keys(rows[0] || {}).slice(0, 8);
  return <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white"><div className="max-h-48 overflow-auto"><table className="w-full text-left text-[11px]"><thead className="sticky top-0 z-10 bg-slate-100"><tr>{columns.map((col) => <th key={col} className="border-b px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">{col.replace(/_/g, " ")}</th>)}</tr></thead><tbody>{rows.slice(0, 8).map((row, idx) => <tr key={idx} className="odd:bg-white even:bg-slate-50/50">{columns.map((col) => <td key={col} className="max-w-[140px] truncate border-b border-slate-100 px-2 py-1.5">{row[col] === null ? <span className="italic text-slate-400">NULL</span> : String(row[col])}</td>)}</tr>)}</tbody></table></div><div className="flex justify-between bg-slate-50 px-2 py-1.5 text-[11px] text-slate-500"><span>{Math.min(rows.length, 8)} of {rows.length} rows</span><span>{columns.length} cols</span></div></div>;
}

function CompareTable({ runs }) {
  if (!runs || runs.length === 0) return <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50 p-8 text-center"><PlayCircle className="h-8 w-8 text-slate-300" /><p className="text-sm font-medium text-slate-500">No comparison runs yet</p><p className="text-xs text-slate-400">Click "Run" to start</p></div>;
  const matched = runs.filter((r) => r.ok && r.hashMatch).length;
  const diffed = runs.filter((r) => r.ok && !r.hashMatch).length;
  const errors = runs.filter((r) => !r.ok).length;
  return <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white"><div className="max-h-52 overflow-auto"><table className="w-full text-left text-[11px]"><thead className="sticky top-0 z-10 bg-slate-100"><tr><th className="border-b px-2 py-2 text-[10px] font-semibold uppercase text-slate-600">Run</th><th className="border-b px-2 py-2 text-[10px] font-semibold uppercase text-slate-600">Metric</th><th className="border-b px-2 py-2 text-right text-[10px] font-semibold uppercase text-slate-600">Live ms</th><th className="border-b px-2 py-2 text-right text-[10px] font-semibold uppercase text-slate-600">ACBP ms</th><th className="border-b px-2 py-2 text-[10px] font-semibold uppercase text-slate-600">Speedup</th><th className="border-b px-2 py-2 text-center text-[10px] font-semibold uppercase text-slate-600">Rows</th><th className="border-b px-2 py-2 text-center text-[10px] font-semibold uppercase text-slate-600">Hash</th><th className="border-b px-2 py-2 text-center text-[10px] font-semibold uppercase text-slate-600">Status</th></tr></thead><tbody>{runs.map((r) => <tr key={r.id} className={`odd:bg-white even:bg-slate-50/50 ${!r.ok ? "bg-rose-50/30" : ""}`}><td className="border-b border-slate-100 px-2 py-2 font-mono text-xs font-bold text-slate-500">#{r.id}</td><td className="border-b border-slate-100 px-2 py-2"><span className="flex items-center gap-1 font-medium">{metricIcons[r.metric]} {metricLabels[r.metric] || r.metric}</span></td><td className="border-b border-slate-100 px-2 py-2 text-right font-mono tabular-nums text-rose-600">{r.liveMs}</td><td className="border-b border-slate-100 px-2 py-2 text-right font-mono tabular-nums text-emerald-600">{r.acbpMs}</td><td className="border-b border-slate-100 px-2 py-2"><SpeedupVisual speedup={r.speedup} /></td><td className="border-b border-slate-100 px-2 py-2 text-center">{r.ok ? <span className="text-xs"><span className="text-rose-500">{r.liveRows}</span><span className="text-slate-300">/</span><span className="text-emerald-500">{r.acbpRows}</span></span> : "—"}</td><td className="border-b border-slate-100 px-2 py-2 text-center">{r.ok ? <SmallBadge tone={r.hashMatch ? "green" : "amber"}>{r.hashMatch ? <><CheckCircle2 className="h-3 w-3" /> match</> : <><AlertTriangle className="h-3 w-3" /> diff</>}</SmallBadge> : "—"}</td><td className="border-b border-slate-100 px-2 py-2 text-center">{r.ok ? <SmallBadge tone="green"><CheckCircle2 className="h-3 w-3" /> ok</SmallBadge> : <SmallBadge tone="red"><XCircle className="h-3 w-3" /> err</SmallBadge>}</td></tr>)}</tbody></table></div><div className="flex justify-between bg-slate-50 px-2 py-1.5 text-[11px] text-slate-500"><span>{runs.length} runs</span><span><span className="text-emerald-600 font-semibold">{matched} matched</span>{" / "}<span className="text-amber-600 font-semibold">{diffed} diff</span>{" / "}<span className="text-rose-600 font-semibold">{errors} err</span></span></div></div>;
}

// ============================================================================
// CHART COMPONENTS
// ============================================================================

function LatencyLineChart() {
  return (
    <div className="chart-wrapper">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={latencySeries} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="iteration" tick={{ fontSize: 10, fill: "#94a3b8" }} tickLine={false} />
          <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} tickLine={false} width={45} />
          <Tooltip contentStyle={{ borderRadius: "10px", border: "1px solid #e2e8f0", fontSize: "11px" }} />
          <Legend wrapperStyle={{ fontSize: "10px" }} />
          <Line type="monotone" dataKey="live" name="Live SQL" stroke="#ef4444" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="acbp" name="ACBP" stroke="#22c55e" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function LiveBarChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="chart-wrapper flex items-center justify-center">
        <div className="text-center">
          <BarChart3 className="mx-auto h-10 w-10 text-slate-300" />
          <p className="mt-2 text-xs text-slate-500">Run comparison to see chart</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chart-wrapper">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 10 }} barSize={24} barGap={6}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="run" tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} />
          <YAxis tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} width={45} />
          <Tooltip contentStyle={{ borderRadius: "10px", border: "1px solid #e2e8f0", fontSize: "11px" }} cursor={{ fill: "rgba(203, 213, 225, 0.2)" }} />
          <Legend wrapperStyle={{ fontSize: "10px" }} />
          <Bar dataKey="live" name="Live SQL" fill="#ef4444" radius={[4, 4, 0, 0]} animationDuration={600} />
          <Bar dataKey="acbp" name="ACBP" fill="#22c55e" radius={[4, 4, 0, 0]} animationDuration={600} animationBegin={200} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ============================================================================
// MAIN APP
// ============================================================================

export default function App() {
  const [mode, setMode] = useState("semantic");
  const [path, setPath] = useState("acbp");
  const [selectedMetric, setSelectedMetric] = useState("census");
  const [hitCount, setHitCount] = useState(5);

  const [health, setHealth] = useState(null);
  const [catalog, setCatalog] = useState({});
  const [queryResult, setQueryResult] = useState(null);
  const [sqlText, setSqlText] = useState("");
  const [loading, setLoading] = useState(false);
  const [multiRunning, setMultiRunning] = useState(false);
  const [compareRuns, setCompareRuns] = useState([]);
  const [progress, setProgress] = useState(0);

  const selectedSemantic = catalog[selectedMetric];
  const modeTitle = mode === "semantic" ? "Semantic BI Layer" : "Direct SQL / No Semantic Layer";
  const modeSubtitle = mode === "semantic" ? "Power BI / SAP-style metric object resolves to Live SQL or ACBP." : "Bypasses semantic names and shows the selected SQL file.";
  const speedupStatic = useMemo(() => (STATIC_SUMMARY.liveMeanMs / STATIC_SUMMARY.acbpMeanMs).toFixed(2), []);
  const compareAverages = useMemo(() => {
    const okRuns = compareRuns.filter((r) => r.ok);
    const liveAvg = mean(okRuns.map((r) => Number(r.liveMs)));
    const acbpAvg = mean(okRuns.map((r) => Number(r.acbpMs)));
    return { liveAvg: liveAvg ? liveAvg.toFixed(2) : "—", acbpAvg: acbpAvg ? acbpAvg.toFixed(2) : "—", speedup: liveAvg && acbpAvg && acbpAvg !== 0 ? (liveAvg / acbpAvg).toFixed(2) : "—" };
  }, [compareRuns]);
  const matchStats = useMemo(() => {
    const ok = compareRuns.filter((r) => r.ok).length;
    const matched = compareRuns.filter((r) => r.ok && r.hashMatch).length;
    return { total: compareRuns.length, ok, matched, matchRate: ok > 0 ? ((matched / ok) * 100).toFixed(1) : "—" };
  }, [compareRuns]);

  const healthStatus = !health ? "checking" : health.ok ? "connected" : "error";

  const loadHealth = useCallback(async () => { try { const res = await fetch("/api/health"); setHealth(await res.json()); } catch (err) { setHealth({ ok: false, error: err instanceof Error ? err.message : "Failed" }); } }, []);
  const loadCatalog = useCallback(async () => { try { const res = await fetch("/api/semantic/catalog"); const data = await res.json(); setCatalog(data.ok ? (data.catalog || {}) : {}); } catch { setCatalog({}); } }, []);
  const runDashboardQuery = useCallback(async () => {
    setLoading(true);
    try {
      const [qRes, sRes] = await Promise.all([fetch(`/api/dashboard/query?ui=${encodeURIComponent(mode)}&engine=${encodeURIComponent(path)}&metric=${encodeURIComponent(selectedMetric)}`), fetch(`/api/dashboard/sql?engine=${encodeURIComponent(path)}&metric=${encodeURIComponent(selectedMetric)}`)]);
      setQueryResult(await qRes.json());
      const sData = await sRes.json();
      setSqlText(sData.ok ? sData.sql : "");
    } catch (err) { setQueryResult({ ok: false, error: err instanceof Error ? err.message : "Request failed" }); setSqlText(""); }
    finally { setLoading(false); }
  }, [mode, path, selectedMetric]);
  const runOne = useCallback(async (engine, metric) => { const res = await fetch(`/api/dashboard/query?ui=${encodeURIComponent(mode)}&engine=${encodeURIComponent(engine)}&metric=${encodeURIComponent(metric)}`); const data = await res.json(); if (!data.ok) throw new Error(data.error || "query failed"); return data; }, [mode]);
  const runMultiHitComparison = useCallback(async () => {
    setMultiRunning(true); setCompareRuns([]); setProgress(0);
    const nextRuns = []; const total = Number(hitCount);
    for (let i = 1; i <= total; i++) {
      try {
        const live = await runOne("live", selectedMetric); const acbp = await runOne("acbp", selectedMetric);
        const liveMs = Number(live.execution.elapsedMs); const acbpMs = Number(acbp.execution.elapsedMs);
        const liveHash = live.execution.resultHash || ""; const acbpHash = acbp.execution.resultHash || "";
        nextRuns.push({ id: i, metric: selectedMetric, liveMs: liveMs.toFixed(2), acbpMs: acbpMs.toFixed(2), speedup: acbpMs !== 0 ? (liveMs / acbpMs).toFixed(2) : "—", liveRows: live.execution.rowCount, acbpRows: acbp.execution.rowCount, liveHash, acbpHash, hashMatch: liveHash !== "" && liveHash === acbpHash, ok: true });
      } catch (err) { nextRuns.push({ id: i, metric: selectedMetric, liveMs: "—", acbpMs: "—", speedup: "—", liveRows: "—", acbpRows: "—", liveHash: "", acbpHash: "", hashMatch: false, ok: false, error: err instanceof Error ? err.message : "failed" }); }
      setCompareRuns([...nextRuns]); setProgress(Math.round((i / total) * 100));
    }
    setMultiRunning(false);
  }, [hitCount, runOne, selectedMetric]);

  useEffect(() => { loadHealth(); loadCatalog(); }, [loadHealth, loadCatalog]);
  useEffect(() => { runDashboardQuery(); }, [runDashboardQuery]);

  const compareChartData = buildCompareChart(compareRuns);

  return (
    <div className="h-screen overflow-hidden bg-gradient-to-br from-slate-50 via-white to-slate-100">
      <div className="h-full overflow-y-auto overflow-x-hidden p-3">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 pb-6">

          {/* HEADER */}
          <div className="shrink-0 overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-slate-800 to-slate-950 p-4 text-white shadow-2xl shadow-slate-900/20 lg:p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="flex items-center gap-2 rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-medium text-emerald-300"><Activity className="h-4 w-4" />ACBP Clinical Dashboard Experiment</div>
                  <StatusDot status={healthStatus} />
                </div>
                <h1 className="text-xl font-bold tracking-tight lg:text-2xl">Semantic vs Direct SQL Dashboard</h1>
                <p className="max-w-2xl text-xs leading-relaxed text-slate-400">Interactive demo showing semantic BI objects, DB-backed query execution, and fresh multi-hit Live SQL vs ACBP comparison with hash verification.</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button active={mode === "semantic"} onClick={() => setMode("semantic")} size="sm"><Sparkles className="h-3.5 w-3.5" /> Semantic</Button>
                <Button active={mode === "direct"} onClick={() => setMode("direct")} size="sm"><Hash className="h-3.5 w-3.5" /> Direct SQL</Button>
                <div className="h-6 w-px bg-slate-700" />
                <Button active={path === "live"} onClick={() => setPath("live")} size="sm">🔴 Live</Button>
                <Button active={path === "acbp"} onClick={() => setPath("acbp")} size="sm">🟢 ACBP</Button>
                <Button onClick={runDashboardQuery} variant="primary" size="sm"><RefreshCcw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />Refresh</Button>
              </div>
            </div>
          </div>

          {/* STAT CARDS */}
          <div className="grid shrink-0 grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
            <StatCard icon={Clock} label="DB Elapsed" value={queryResult?.execution?.elapsedMs !== undefined ? `${queryResult.execution.elapsedMs} ms` : "—"} sub={queryResult?.execution?.sqlFile || "Awaiting..."} tone={path === "acbp" ? "green" : "red"} />
            <StatCard icon={Database} label="Rows" value={queryResult?.execution?.rowCount ?? "—"} sub={`${metricLabels[selectedMetric]} / ${path.toUpperCase()}`} tone="blue" />
            <StatCard icon={ShieldCheck} label="Hash" value={queryResult?.execution?.resultHash ? "SHA-256 ✓" : "—"} sub={queryResult?.execution?.resultHash?.slice(0, 14) || "Not loaded"} tone="amber" />
            <StatCard icon={Zap} label="Paper Speedup" value={`${speedupStatic}x`} sub="Static result" tone="green" />
            <StatCard icon={BarChart3} label="Buffer Ratio" value={`${STATIC_SUMMARY.bufferRatio}x`} sub={`${STATIC_SUMMARY.bufferReductionPct}% reduction`} tone="purple" />
            <StatCard icon={Target} label="Correctness" value={STATIC_SUMMARY.hashMatchRate} sub={`${STATIC_SUMMARY.pairedComparisons} pairs`} tone="green" />
          </div>

          {/* TOP ROW: Semantic | DB Result | Latency Chart */}
          <div className="grid gap-3 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <div><CardTitle>{modeTitle}</CardTitle><CardDescription>{modeSubtitle}</CardDescription></div>
                <div className="flex rounded-xl bg-slate-100 p-0.5">
                  {Object.entries(metricLabels).map(([key, label]) => <button key={key} type="button" onClick={() => setSelectedMetric(key)} className={`rounded-lg px-2 py-1 text-[11px] font-medium transition-all ${selectedMetric === key ? "bg-white text-slate-900 shadow-sm" : "text-slate-500"}`}>{metricIcons[key]} {label}</button>)}
                </div>
              </CardHeader>
              <CardContent>
                {mode === "semantic" ? <SemanticPanel selectedSemantic={selectedSemantic} queryResult={queryResult} path={path} selectedMetric={selectedMetric} /> : <pre className="min-h-[200px] whitespace-pre-wrap rounded-2xl bg-slate-950 p-3 text-[11px] leading-relaxed text-emerald-100">{sqlText || "-- SQL not loaded yet."}</pre>}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div><CardTitle icon={Table2}>DB Result</CardTitle><CardDescription>Live PostgreSQL data</CardDescription></div>
                {loading && <SmallBadge tone="blue" pulse>Running...</SmallBadge>}
              </CardHeader>
              <CardContent>
                {loading ? <div className="flex flex-col items-center justify-center gap-3 py-8"><RefreshCcw className="h-8 w-8 animate-spin text-slate-400" /><p className="text-xs text-slate-500">Executing query...</p></div> : queryResult?.ok ? <RowsPreview rows={queryResult.execution.rows} /> : <div className="rounded-2xl border-2 border-rose-200 bg-rose-50 p-4"><div className="flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-rose-500" /><p className="text-xs font-semibold text-rose-700">{queryResult?.error || "No result yet."}</p></div></div>}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div><CardTitle>📈 Latency Trend</CardTitle><CardDescription>Static paper trend (reference)</CardDescription></div>
              </CardHeader>
              <CardContent><LatencyLineChart /></CardContent>
            </Card>
          </div>

          {/* BOTTOM ROW: Multi-Hit | Bar Chart */}
          <div className="grid gap-3 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <div><CardTitle icon={Target}>Multi-Hit Comparison</CardTitle><CardDescription>Repeated Live SQL vs ACBP with hash verification</CardDescription></div>
                <div className="flex flex-wrap items-center gap-2">
                  <select value={hitCount} onChange={(e) => setHitCount(Number(e.target.value))} className="h-8 rounded-xl border-2 border-slate-200 bg-white px-2 text-xs font-medium">{hitOptions.map((n) => <option key={n} value={n}>{n} hits</option>)}</select>
                  <Button onClick={runMultiHitComparison} disabled={multiRunning} variant="primary" size="sm"><PlayCircle className="h-3.5 w-3.5" />{multiRunning ? `Running ${progress}%` : "Run"}</Button>
                </div>
              </CardHeader>
              {multiRunning && <ProgressBar value={progress} max={100} />}
              <div className="grid grid-cols-3 gap-2 px-4 pb-2">
                <StatCard icon={Clock} label="Live Avg" value={compareAverages.liveAvg === "—" ? "—" : `${compareAverages.liveAvg} ms`} sub="API hits" tone="red" />
                <StatCard icon={Clock} label="ACBP Avg" value={compareAverages.acbpAvg === "—" ? "—" : `${compareAverages.acbpAvg} ms`} sub="API hits" tone="green" />
                <StatCard icon={Zap} label="Speedup" value={compareAverages.speedup === "—" ? "—" : `${compareAverages.speedup}x`} sub={matchStats.total > 0 ? `${matchStats.matchRate}% match` : "fresh"} tone={Number(compareAverages.speedup) >= 1.5 ? "green" : "amber"} />
              </div>
              <CardContent><CompareTable runs={compareRuns} /></CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div><CardTitle icon={BarChart3}>Live Run Chart</CardTitle><CardDescription>Fresh multi-hit results (not paper data)</CardDescription></div>
                {compareChartData.length > 0 && <SmallBadge tone="blue">{compareChartData.length} runs</SmallBadge>}
              </CardHeader>
              <CardContent><LiveBarChart data={compareChartData} /></CardContent>
              <CardFooter><p className="font-bold">📋 Note</p><p>"Paper" cards = fixed experiment results. Multi-hit table & chart = fresh local measurements.</p></CardFooter>
            </Card>
          </div>

        </div>
      </div>
    </div>
  );
}