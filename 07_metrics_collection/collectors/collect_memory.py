#!/usr/bin/env python3
"""
collect_memory.py
Samples Docker container memory usage (used / limit) and percent.

Outputs:
  ACBP_Clinical_Dashboard_Experiment/07_metrics_collection/raw_logs/memory.csv
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


def docker_mem(container: str):
    cmd = f'docker stats {container} --no-stream --format "{{{{.MemUsage}}}},{{{{.MemPerc}}}}"'
    out = subprocess.check_output(cmd, shell=True, text=True).strip()
    mem_usage, mem_perc = out.split(",", 1)
    used, limit = mem_usage.split(" / ", 1)
    return used.strip(), limit.strip(), mem_perc.replace("%", "").strip()


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
    ap.add_argument("--container", default="acbp-postgres")
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--interval_seconds", type=float, default=0.0)
    args = ap.parse_args()

    root = Path("ACBP_Clinical_Dashboard_Experiment")
    out = root / "07_metrics_collection" / "raw_logs" / "memory.csv"
    header = ["timestamp_utc", "mem_used", "mem_limit", "mem_percent"]

    for i in range(args.samples):
        ts = utc_now_iso()
        try:
            used, limit, perc = docker_mem(args.container)
            append_row(out, header, [ts, used, limit, perc])
        except Exception:
            append_row(out, header, [ts, "ERROR", "ERROR", "ERROR"])
        if args.interval_seconds > 0 and i < args.samples - 1:
            time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()