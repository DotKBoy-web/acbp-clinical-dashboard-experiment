#!/usr/bin/env python3
"""
collect_buffers.py (FINAL)

Runs the dedicated EXPLAIN SQL files and extracts TOTAL shared hit blocks by
summing all 'Buffers: shared hit=...' occurrences.

Output:
  ACBP_Clinical_Dashboard_Experiment/07_metrics_collection/raw_logs/buffers.csv
"""

import argparse
import csv
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc
BUFF_RE = re.compile(r"Buffers:\s+shared hit=(\d+)", re.IGNORECASE)

def utc_now_iso():
    return datetime.now(tz=UTC).isoformat()

def run_cmd(cmd: str, timeout: int):
    t0 = time.perf_counter()
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        ms = (time.perf_counter() - t0) * 1000.0
        return p.returncode, p.stdout or "", p.stderr or "", ms
    except subprocess.TimeoutExpired:
        ms = (time.perf_counter() - t0) * 1000.0
        return 124, "", "TIMEOUT", ms

def parse_total_shared_hit(stdout: str):
    hits = BUFF_RE.findall(stdout)
    if not hits:
        return None
    return sum(int(x) for x in hits)

def append_csv(path: Path, header, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(header)
        w.writerow(row)

def build_psql_pipe_cmd(container: str, user: str, db: str, sql_file: Path) -> str:
    return (
        'powershell -ExecutionPolicy Bypass -Command '
        f'"Get-Content -Raw \'{sql_file.as_posix()}\' | '
        f'docker exec -i {container} psql -X -q -v ON_ERROR_STOP=1 -U {user} -d {db}"'
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--container", default="acbp-postgres")
    ap.add_argument("--db_name", default="acbp_db")
    ap.add_argument("--db_user", default="acbp")
    ap.add_argument("--timeout_seconds", type=int, default=600)
    args = ap.parse_args()

    root = Path("ACBP_Clinical_Dashboard_Experiment")
    live_explain = root / "03_live_query_model/sql/live_dashboard_explain.sql"
    cbp_explain  = root / "04_cbp_model/sql/cbp_dashboard_explain.sql"

    out = root / "07_metrics_collection/raw_logs/buffers.csv"
    header = ["timestamp_utc","condition","ok","elapsed_ms","shared_hit_total","stderr_preview"]

    for cond, sqlf in [("live", live_explain), ("cbp", cbp_explain)]:
        cmd = build_psql_pipe_cmd(args.container, args.db_user, args.db_name, sqlf)
        ts = utc_now_iso()
        rc, so, se, ms = run_cmd(cmd, timeout=args.timeout_seconds)
        ok = 1 if rc == 0 else 0
        hit = parse_total_shared_hit(so) if ok else None
        append_csv(out, header, [
            ts, cond, ok, round(ms,2),
            (hit if hit is not None else ""),
            (se.strip()[:160] if se else "")
        ])

    print(f"✅ Buffers written to: {out}")

if __name__ == "__main__":
    main()