import express from "express";
import cors from "cors";
import pg from "pg";
import fs from "fs";
import path from "path";
import crypto from "crypto";
import { performance } from "perf_hooks";

const Pool = pg.Pool;

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.UI_DEMO_API_PORT || 5174;
const repoRoot = path.resolve(process.cwd(), "../..");

const pool = new Pool({
  host: process.env.PGHOST || "127.0.0.1",
  port: Number(process.env.PGPORT || 55432),
  database: process.env.PGDATABASE || "acbp_db",
  user: process.env.PGUSER || "acbp",
  password: process.env.PGPASSWORD || "acbp"
});

const queryFiles = {
  live: {
    census: path.join(repoRoot, "03_live_query_model", "sql", "live_dashboard_query.sql"),
    discharge: path.join(repoRoot, "03_live_query_model", "sql", "live_dashboard_query.sql"),
    occupancy: path.join(repoRoot, "03_live_query_model", "sql", "live_dashboard_query.sql")
  },
  acbp: {
    census: path.join(repoRoot, "04_cbp_model", "sql", "cbp_dashboard_query.sql"),
    discharge: path.join(repoRoot, "04_cbp_model", "sql", "cbp_dashboard_query.sql"),
    occupancy: path.join(repoRoot, "04_cbp_model", "sql", "cbp_dashboard_query.sql")
  }
};

const explainFiles = {
  live: path.join(repoRoot, "03_live_query_model", "sql", "live_dashboard_explain.sql"),
  acbp: path.join(repoRoot, "04_cbp_model", "sql", "cbp_dashboard_explain.sql")
};

const semanticCatalog = {
  census: {
    label: "Census Count",
    powerbiObject: "Power BI Measure: Live Census",
    sapObject: "SAP Universe Measure: Census Count",
    description: "Counts active inpatient census membership using temporal location state and encounter status.",
    liveResolution: "The semantic object resolves to the validated full Live SQL dashboard query, which computes census from runtime encounter, location, order, and facility hierarchy logic.",
    acbpResolution: "The semantic object resolves to the validated full ACBP dashboard query, which reads precomputed state surfaces and compiled decision-space structures."
  },
  discharge: {
    label: "Discharge Count",
    powerbiObject: "Power BI Measure: Discharge Events",
    sapObject: "SAP Universe Measure: Discharge Count",
    description: "Counts discharge-related workflow events using encounter timestamps and discharge-order signals.",
    liveResolution: "The semantic object resolves to the validated full Live SQL dashboard query, including discharge flags and discharge-order timing logic.",
    acbpResolution: "The semantic object resolves to the validated full ACBP dashboard query, including prevalidated discharge-related Boolean state."
  },
  occupancy: {
    label: "Occupancy Ratio",
    powerbiObject: "Power BI Measure: Occupancy Ratio",
    sapObject: "SAP Universe Measure: Occupancy %",
    description: "Computes occupied beds over reference capacity using facility, unit, room, and bed context.",
    liveResolution: "The semantic object resolves to the validated full Live SQL dashboard query, including runtime capacity and occupied-bed logic.",
    acbpResolution: "The semantic object resolves to the validated full ACBP dashboard query, including compiled categorical context and occupancy state."
  }
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function normalizeRelative(filePath) {
  return path.relative(repoRoot, filePath).replaceAll("\\", "/");
}

function validateEngine(engine) {
  return engine === "live" || engine === "acbp";
}

function validateMetric(metric) {
  return metric === "census" || metric === "discharge" || metric === "occupancy";
}

function validateUi(ui) {
  return ui === "semantic" || ui === "direct";
}

function getQueryFile(engine, metric) {
  if (!validateEngine(engine)) {
    throw new Error("engine must be live or acbp");
  }

  if (!validateMetric(metric)) {
    throw new Error("metric must be census, discharge, or occupancy");
  }

  if (!queryFiles[engine] || !queryFiles[engine][metric]) {
    throw new Error("No SQL file configured for engine=" + engine + ", metric=" + metric);
  }

  return queryFiles[engine][metric];
}

function cleanSqlText(sql) {
  const backtick = String.fromCharCode(96);
  const fence3 = backtick + backtick + backtick;
  const fence2 = backtick + backtick;

  let cleaned = sql;
  cleaned = cleaned.split(fence3 + "sql").join("");
  cleaned = cleaned.split(fence3 + "SQL").join("");
  cleaned = cleaned.split(fence3).join("");
  cleaned = cleaned.split(fence2).join("");

  cleaned = cleaned
    .split(/\r?\n/)
    .filter(function (line) {
      return !line.trim().startsWith("\\");
    })
    .join("\n");

  return cleaned.trim();
}

function readSql(filePath) {
  if (!fs.existsSync(filePath)) {
    throw new Error("SQL file not found: " + filePath);
  }

  const rawSql = fs.readFileSync(filePath, "utf8");
  return cleanSqlText(rawSql);
}

// ============================================================================
// CBP MATERIALIZED VIEW REFRESH
// This ensures ACBP and Live SQL use the same time context (now())
// ============================================================================

async function refreshCbpMaterializedViews() {
  try {
    console.log("[" + new Date().toISOString() + "] Refreshing CBP materialized views...");
    const refreshStart = performance.now();
    await pool.query("SELECT cbp.refresh_fac01_all(true);");
    const refreshMs = Number((performance.now() - refreshStart).toFixed(2));
    console.log("[" + new Date().toISOString() + "] CBP materialized views refreshed in " + refreshMs + "ms");
  } catch (err) {
    console.error("Failed to refresh CBP materialized views:", err.message);
    throw new Error("CBP materialized view refresh failed: " + err.message);
  }
}

// ============================================================================
// HASH NORMALIZATION FUNCTIONS
// ============================================================================

function normalizeValue(value) {
  if (value === undefined || value === null) {
    return null;
  }

  if (value instanceof Date) {
    return value.toISOString();
  }

  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      return null;
    }
    return Number(value.toFixed(10));
  }

  if (typeof value === "bigint") {
    return Number(value);
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  if (typeof value === "string") {
    return value.trim();
  }

  return String(value);
}

function normalizeRows(rows) {
  if (!rows || rows.length === 0) {
    return [];
  }

  const columns = Object.keys(rows[0]).sort();

  const normalizedRows = rows.map(function (row) {
    const normalized = {};
    columns.forEach(function (col) {
      normalized[col] = normalizeValue(row[col]);
    });
    return normalized;
  });

  normalizedRows.sort(function (a, b) {
    const aStr = JSON.stringify(a);
    const bStr = JSON.stringify(b);
    return aStr.localeCompare(bStr);
  });

  return normalizedRows;
}

function hashRows(rows) {
  const normalizedRows = normalizeRows(rows);
  const json = JSON.stringify(normalizedRows);
  return crypto.createHash("sha256").update(json).digest("hex");
}

// ============================================================================
// QUERY EXECUTION
// ============================================================================

async function runSqlFile(engine, metric) {
  // Refresh materialized views BEFORE running ACBP query
  // This ensures both engines use the same now() context
  if (engine === "acbp") {
    await refreshCbpMaterializedViews();
  }

  const file = getQueryFile(engine, metric);
  const sql = readSql(file);

  const started = performance.now();

  let result;

  try {
    result = await pool.query(sql);
  } catch (err) {
    throw new Error(
      "Failed SQL file: " +
      normalizeRelative(file) +
      " | PostgreSQL error: " +
      err.message
    );
  }

  const ended = performance.now();

  const resultHash = hashRows(result.rows);

  console.log(
    "[" + new Date().toISOString() + "]",
    "Engine:", engine,
    "| Metric:", metric,
    "| Rows:", result.rows.length,
    "| Elapsed:", Number((ended - started).toFixed(2)) + "ms",
    "| Hash:", resultHash.substring(0, 16) + "..."
  );

  return {
    engine: engine,
    metric: metric,
    sqlFile: normalizeRelative(file),
    elapsedMs: Number((ended - started).toFixed(2)),
    rowCount: result.rowCount !== null && result.rowCount !== undefined ? result.rowCount : result.rows.length,
    rows: result.rows,
    resultHash: resultHash
  };
}

// ============================================================================
// API ROUTES
// ============================================================================

app.get("/api/health", async function (req, res) {
  try {
    const db = await pool.query("select version() as version, now() as server_time");

    res.json({
      ok: true,
      api: "ACBP dashboard UI demo API",
      repoRoot: repoRoot,
      database: db.rows[0],
      queryFiles: {
        live: {
          census: normalizeRelative(queryFiles.live.census),
          discharge: normalizeRelative(queryFiles.live.discharge),
          occupancy: normalizeRelative(queryFiles.live.occupancy)
        },
        acbp: {
          census: normalizeRelative(queryFiles.acbp.census),
          discharge: normalizeRelative(queryFiles.acbp.discharge),
          occupancy: normalizeRelative(queryFiles.acbp.occupancy)
        }
      },
      explainFiles: {
        live: normalizeRelative(explainFiles.live),
        acbp: normalizeRelative(explainFiles.acbp)
      }
    });
  } catch (err) {
    res.status(500).json({
      ok: false,
      error: err.message
    });
  }
});

app.get("/api/semantic/catalog", function (req, res) {
  res.json({
    ok: true,
    catalog: semanticCatalog
  });
});

app.get("/api/dashboard/query", async function (req, res) {
  const ui = req.query.ui || "semantic";
  const engine = req.query.engine || "acbp";
  const metric = req.query.metric || "census";

  if (!validateUi(ui)) {
    return res.status(400).json({
      ok: false,
      error: "ui must be semantic or direct"
    });
  }

  if (!validateEngine(engine)) {
    return res.status(400).json({
      ok: false,
      error: "engine must be live or acbp"
    });
  }

  if (!validateMetric(metric)) {
    return res.status(400).json({
      ok: false,
      error: "metric must be census, discharge, or occupancy"
    });
  }

  try {
    const semantic = semanticCatalog[metric];
    const execution = await runSqlFile(engine, metric);

    let resolution = "";

    if (ui === "semantic") {
      if (engine === "live") {
        resolution = semantic.liveResolution;
      } else {
        resolution = semantic.acbpResolution;
      }
    } else {
      resolution = "Direct SQL mode bypasses semantic object naming and executes the validated dashboard SQL file for the selected engine.";
    }

    res.json({
      ok: true,
      ui: ui,
      engine: engine,
      metric: metric,
      semantic: semantic,
      resolution: resolution,
      execution: execution
    });
  } catch (err) {
    res.status(500).json({
      ok: false,
      ui: ui,
      engine: engine,
      metric: metric,
      error: err.message
    });
  }
});

app.get("/api/dashboard/sql", function (req, res) {
  const engine = req.query.engine || "acbp";
  const metric = req.query.metric || "census";

  if (!validateEngine(engine)) {
    return res.status(400).json({
      ok: false,
      error: "engine must be live or acbp"
    });
  }

  if (!validateMetric(metric)) {
    return res.status(400).json({
      ok: false,
      error: "metric must be census, discharge, or occupancy"
    });
  }

  try {
    const file = getQueryFile(engine, metric);

    res.json({
      ok: true,
      engine: engine,
      metric: metric,
      sqlFile: normalizeRelative(file),
      sql: readSql(file)
    });
  } catch (err) {
    res.status(500).json({
      ok: false,
      engine: engine,
      metric: metric,
      error: err.message
    });
  }
});

app.get("/api/experiment/summary", function (req, res) {
  res.json({
    ok: true,
    correctness: {
      pairedComparisons: 48,
      hashMatchRate: "100%",
      mismatches: 0
    },
    latency: {
      liveMeanMs: 416.41,
      liveMedianMs: 409.05,
      liveP95Ms: 467.63,
      acbpMeanMs: 211.97,
      acbpMedianMs: 204.56,
      acbpP95Ms: 249.62,
      meanSpeedup: 1.992
    },
    buffers: {
      pairedSamples: 5,
      meanRatioLiveOverAcbp: 8.681,
      meanReductionPercent: 88.48
    }
  });
});

app.use(function (req, res) {
  res.status(404).json({
    ok: false,
    error: "API route not found",
    path: req.path
  });
});

// ============================================================================
// START SERVER
// ============================================================================

app.listen(PORT, function () {
  console.log("=".repeat(60));
  console.log("ACBP UI demo API running on http://localhost:" + PORT);
  console.log("CBP materialized view refresh: ENABLED (before each ACBP query)");
  console.log("Hash normalization: ENABLED");
  console.log("=".repeat(60));
});