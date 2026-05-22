#!/usr/bin/env python3
"""
collect_refresh_time.py (FINAL - stable + TEXT buffers)

Outputs:
  - ACBP_Clinical_Dashboard_Experiment/07_metrics_collection/raw_logs/combined_metrics.csv
  - ACBP_Clinical_Dashboard_Experiment/07_metrics_collection/raw_logs/live_query/latency.csv
  - ACBP_Clinical_Dashboard_Experiment/07_metrics_collection/raw_logs/cbp/latency.csv
"""

import argparse
import csv
import hashlib
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc

BUFF_RE = re.compile(r"Buffers:\s+shared hit=(\d+)", re.IGNORECASE)

def utc_now_iso():
    return datetime.now(tz=UTC).isoformat()

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()

def run_cmd(cmd: str, timeout: int = None):
    t0 = time.perf_counter()
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        ms = (time.perf_counter() - t0) * 1000.0
        return p.returncode, p.stdout or "", p.stderr or "", ms
    except subprocess.TimeoutExpired:
        ms = (time.perf_counter() - t0) * 1000.0
        return 124, "", "TIMEOUT", ms

def append_csv(path: Path, header, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(header)
        w.writerow(row)

def docker_cpu_percent(container: str) -> str:
    try:
        cmd = f'docker stats {container} --no-stream --format "{{{{.CPUPerc}}}}"'
        return subprocess.check_output(cmd, shell=True, text=True).strip().replace("%","").strip()
    except Exception:
        return "ERROR"

def docker_mem(container: str):
    try:
        cmd = f'docker stats {container} --no-stream --format "{{{{.MemUsage}}}},{{{{.MemPerc}}}}"'
        out = subprocess.check_output(cmd, shell=True, text=True).strip()
        usage, perc = out.split(",", 1)
        used, limit = usage.split(" / ", 1)
        return used.strip(), limit.strip(), perc.replace("%","").strip()
    except Exception:
        return "ERROR","ERROR","ERROR"

def parse_psql_single_row(stdout: str):
    lines = [ln.strip("\r\n") for ln in stdout.splitlines() if ln.strip()]
    sep_idx = None
    for i, ln in enumerate(lines):
        if set(ln) <= set("-+"):
            sep_idx = i
            break
    if sep_idx is None or sep_idx + 1 >= len(lines):
        return None
    data_line = lines[sep_idx + 1]
    if data_line.startswith("("):
        return None
    return data_line

def parse_total_shared_hit(explain_stdout: str):
    hits = BUFF_RE.findall(explain_stdout)
    if not hits:
        return None
    return sum(int(x) for x in hits)

def build_psql_pipe_cmd(container: str, db_user: str, db_name: str, sql_file: Path) -> str:
    return (
        'powershell -ExecutionPolicy Bypass -Command '
        f'"Get-Content -Raw \'{sql_file.as_posix()}\' | '
        f'docker exec -i {container} psql -X -q -v ON_ERROR_STOP=1 -U {db_user} -d {db_name}"'
    )

def build_psql_inline_cmd(container: str, db_user: str, db_name: str, sql: str) -> str:
    sql_clean = sql.strip().rstrip(";").replace('"', '\\"')
    return f'docker exec -i {container} psql -X -q -v ON_ERROR_STOP=1 -U {db_user} -d {db_name} -c "{sql_clean};"'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=30)
    ap.add_argument("--sleep_seconds", type=float, default=1.0)
    ap.add_argument("--timeout_seconds", type=int, default=600)

    ap.add_argument("--with_feed", action="store_true")
    ap.add_argument("--feed_admissions", type=int, default=5)
    ap.add_argument("--feed_transfers", type=int, default=3)
    ap.add_argument("--feed_discharges", type=int, default=2)

    ap.add_argument("--with_buffers", action="store_true")
    ap.add_argument("--buffers_every", type=int, default=10)

    ap.add_argument("--container", default="acbp-postgres")
    ap.add_argument("--db_name", default="acbp_db")
    ap.add_argument("--db_user", default="acbp")
    ap.add_argument("--db_password", default="acbp")

    args = ap.parse_args()

    root = Path("ACBP_Clinical_Dashboard_Experiment")

    live_sql = root / "03_live_query_model" / "sql" / "live_dashboard_query.sql"
    live_explain_sql = root / "03_live_query_model" / "sql" / "live_dashboard_explain.sql"
    cbp_explain_sql = root / "04_cbp_model" / "sql" / "cbp_dashboard_explain.sql"

    cbp_sql_inline = "SELECT * FROM cbp.fac01_dashboard_kpis;"

    feed_ps1 = root / "05_live_feed_simulation" / "feed_scripts" / "run_feed_cycle.ps1"

    out_combined = root / "07_metrics_collection" / "raw_logs" / "combined_metrics.csv"
    out_live = root / "07_metrics_collection" / "raw_logs" / "live_query" / "latency.csv"
    out_cbp  = root / "07_metrics_collection" / "raw_logs" / "cbp" / "latency.csv"

    header = [
        "timestamp_utc","iteration","condition","ok",
        "elapsed_ms","cpu_percent","mem_used","mem_limit","mem_percent",
        "shared_hit",
        "result_hash","result_preview","stderr_preview"
    ]

    live_cmd = build_psql_pipe_cmd(args.container, args.db_user, args.db_name, live_sql)
    cbp_cmd  = build_psql_inline_cmd(args.container, args.db_user, args.db_name, cbp_sql_inline)

    live_explain_cmd = build_psql_pipe_cmd(args.container, args.db_user, args.db_name, live_explain_sql)
    cbp_explain_cmd  = build_psql_pipe_cmd(args.container, args.db_user, args.db_name, cbp_explain_sql)

    feed_cmd = (
        f'powershell -ExecutionPolicy Bypass -File "{feed_ps1.as_posix()}" '
        f'-Admissions {args.feed_admissions} -Transfers {args.feed_transfers} -Discharges {args.feed_discharges} '
        f'-DbName {args.db_name} -DbUser {args.db_user} -DbPass {args.db_password} '
        f'-Container {args.container}'
    )

    for i in range(1, args.iterations + 1):
        ts = utc_now_iso()

        # Feed cycle row (optional)
        if args.with_feed:
            rc, so, se, ms = run_cmd(feed_cmd, timeout=args.timeout_seconds)
            ok = 1 if rc == 0 else 0
            cpu = docker_cpu_percent(args.container)
            mu, ml, mp = docker_mem(args.container)
            append_csv(out_combined, header, [
                ts, i, "feed_cycle", ok, round(ms, 2), cpu, mu, ml, mp,
                "", sha256_text(so + se), (so.strip()[:160] if so else ""), (se.strip()[:160] if se else "")
            ])
            if not ok:
                time.sleep(args.sleep_seconds)
                continue

        # Buffer samples (only on selected iterations)
        do_buf = args.with_buffers and args.buffers_every > 0 and (i % args.buffers_every == 0)
        live_hit = cbp_hit = None
        live_buf_err = cbp_buf_err = ""

        if do_buf:
            rc, so, se, _ = run_cmd(live_explain_cmd, timeout=args.timeout_seconds)
            live_hit = parse_total_shared_hit(so) if rc == 0 else None
            if live_hit is None:
                live_buf_err = (se.strip()[:160] if se else "NO_LIVE_BUFFERS")

            rc, so, se, _ = run_cmd(cbp_explain_cmd, timeout=args.timeout_seconds)
            cbp_hit = parse_total_shared_hit(so) if rc == 0 else None
            if cbp_hit is None:
                cbp_buf_err = (se.strip()[:160] if se else "NO_CBP_BUFFERS")

        # LIVE query row
        rc, out, err, ms = run_cmd(live_cmd, timeout=args.timeout_seconds)
        ok = 1 if rc == 0 else 0
        cpu = docker_cpu_percent(args.container)
        mu, ml, mp = docker_mem(args.container)
        rowdata = parse_psql_single_row(out) if ok else None
        preview = (rowdata[:160] if rowdata else (out.strip()[:160] if out else ""))
        h = sha256_text(rowdata if rowdata else (out + err))
        err_preview = (err.strip()[:120] if err else "")
        if do_buf and live_buf_err:
            err_preview = (err_preview + " | BUF: " + live_buf_err)[:120]
        row_live = [ts, i, "live", ok, round(ms, 2), cpu, mu, ml, mp,
                    (live_hit if live_hit is not None else ""), h, preview, err_preview]
        append_csv(out_live, header, row_live)
        append_csv(out_combined, header, row_live)

        # CBP query row
        rc, out, err, ms = run_cmd(cbp_cmd, timeout=args.timeout_seconds)
        ok = 1 if rc == 0 else 0
        cpu = docker_cpu_percent(args.container)
        mu, ml, mp = docker_mem(args.container)
        rowdata = parse_psql_single_row(out) if ok else None
        preview = (rowdata[:160] if rowdata else (out.strip()[:160] if out else ""))
        h = sha256_text(rowdata if rowdata else (out + err))
        err_preview = (err.strip()[:120] if err else "")
        if do_buf and cbp_buf_err:
            err_preview = (err_preview + " | BUF: " + cbp_buf_err)[:120]
        row_cbp = [ts, i, "cbp", ok, round(ms, 2), cpu, mu, ml, mp,
                   (cbp_hit if cbp_hit is not None else ""), h, preview, err_preview]
        append_csv(out_cbp, header, row_cbp)
        append_csv(out_combined, header, row_cbp)

        time.sleep(args.sleep_seconds)

if __name__ == "__main__":
    main()