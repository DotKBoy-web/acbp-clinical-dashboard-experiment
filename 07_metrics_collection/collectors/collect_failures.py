#!/usr/bin/env python3
"""
collect_failures.py
Logs success/failure events for feed cycles and queries.
Outputs:
  ACBP_Clinical_Dashboard_Experiment/07_metrics_collection/raw_logs/failures.csv
"""

import argparse
import csv
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc


def utc_now_iso():
    return datetime.now(tz=UTC).isoformat()


def run_cmd(cmd: str, timeout: int):
    t0 = time.perf_counter()
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    ms = (time.perf_counter() - t0) * 1000.0
    return p.returncode, p.stdout or "", p.stderr or "", ms


def append_row(path: Path, header, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(header)
        w.writerow(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=1)
    ap.add_argument("--sleep_seconds", type=float, default=0.0)
    ap.add_argument("--timeout_seconds", type=int, default=180)

    ap.add_argument("--run_feed", action="store_true")
    ap.add_argument("--run_live", action="store_true")
    ap.add_argument("--run_cbp", action="store_true")
    ap.add_argument("--run_refresh", action="store_true")

    ap.add_argument("--container", default="acbp-postgres")
    ap.add_argument("--db_name", default="acbp_db")
    ap.add_argument("--db_user", default="acbp")

    ap.add_argument("--live_sql_file",
                    default="ACBP_Clinical_Dashboard_Experiment/03_live_query_model/sql/live_dashboard_query.sql")
    ap.add_argument("--feed_ps1",
                    default="ACBP_Clinical_Dashboard_Experiment/05_live_feed_simulation/feed_scripts/run_feed_cycle.ps1")

    args = ap.parse_args()

    root = Path("ACBP_Clinical_Dashboard_Experiment")
    out = root / "07_metrics_collection" / "raw_logs" / "failures.csv"

    header = ["timestamp_utc", "iteration", "component", "ok", "return_code", "elapsed_ms", "stderr_preview"]

    feed_cmd = f'powershell -ExecutionPolicy Bypass -File "{args.feed_ps1}"'
    live_cmd = (
        f'powershell -ExecutionPolicy Bypass -Command '
        f'"Get-Content -Raw \'{Path(args.live_sql_file).as_posix()}\' | '
        f'docker exec -i {args.container} psql -U {args.db_user} -d {args.db_name}"'
    )
    cbp_cmd = f'docker exec -i {args.container} psql -U {args.db_user} -d {args.db_name} -c "SELECT * FROM cbp.fac01_dashboard_kpis;"'
    refresh_cmd = f'docker exec -i {args.container} psql -U {args.db_user} -d {args.db_name} -c "SELECT cbp.refresh_fac01_all(true);"'

    for i in range(1, args.iterations + 1):
        ts = utc_now_iso()

        def do(component, cmd):
            rc, so, se, ms = run_cmd(cmd, args.timeout_seconds)
            append_row(out, header, [ts, i, component, 1 if rc == 0 else 0, rc, round(ms, 3), (se.strip()[:250] if se else "")])

        if args.run_feed:
            do("feed_cycle", feed_cmd)
        if args.run_live:
            do("live_query", live_cmd)
        if args.run_refresh:
            do("cbp_refresh", refresh_cmd)
        if args.run_cbp:
            do("cbp_query", cbp_cmd)

        if args.sleep_seconds > 0 and i < args.iterations:
            time.sleep(args.sleep_seconds)


if __name__ == "__main__":
    main()
