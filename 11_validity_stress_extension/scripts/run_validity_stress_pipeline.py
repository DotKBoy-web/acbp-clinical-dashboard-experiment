#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print("Missing dependency: psycopg2")
    print("Install it with:")
    print("  pip install psycopg2-binary")
    sys.exit(1)


SQL_FILES = [
    "00_create_extension_schema.sql",
    "01_build_live_observed_surface.sql",
    "02_build_cbp_observed_surface.sql",
    "03_build_synthetic_invalid_space.sql",
    "04_apply_acbp_validity_labels.sql",
    "05_dotk_complexity_summary.sql",
    "06_export_ml_dataset.sql",
]


def connect(args):
    kwargs = {
        "host": args.host,
        "port": args.port,
        "dbname": args.db,
        "user": args.user,
    }

    password = args.password or os.environ.get("PGPASSWORD")
    if password:
        kwargs["password"] = password

    return psycopg2.connect(**kwargs)


def run_sql_file(conn, sql_path):
    print(f"Running SQL: {sql_path.name}")
    sql = sql_path.read_text(encoding="utf-8")

    with conn.cursor() as cur:
        cur.execute(sql)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=55432, type=int)
    parser.add_argument("--db", default="acbp_db")
    parser.add_argument("--user", default="acbp")
    parser.add_argument("--password", default="acbp")
    parser.add_argument(
        "--root",
        default=r"D:\ICDM2026\ACBP_Clinical_Dashboard_Experiment",
    )
    args = parser.parse_args()

    root = Path(args.root)
    ext = root / "11_validity_stress_extension"
    sql_dir = ext / "sql"
    outdir = ext / "outputs"
    ml_script = ext / "scripts" / "run_validity_ml.py"

    print("Running ACBP validity-stress extension through Python...")
    print(f"Repo root: {root}")
    print(f"Extension: {ext}")

    conn = connect(args)
    conn.autocommit = True

    try:
        for file_name in SQL_FILES:
            sql_path = sql_dir / file_name
            if not sql_path.exists():
                raise FileNotFoundError(f"Missing SQL file: {sql_path}")
            run_sql_file(conn, sql_path)
    finally:
        conn.close()

    print("SQL pipeline complete.")
    print("Running ML diagnostic...")

    cmd = [
        sys.executable,
        str(ml_script),
        "--host", args.host,
        "--port", str(args.port),
        "--db", args.db,
        "--user", args.user,
        "--outdir", str(outdir),
    ]

    if args.password:
        cmd.extend(["--password", args.password])

    subprocess.run(cmd, check=True)

    print("Validity-stress extension complete.")
    print(f"Outputs saved to: {outdir}")


if __name__ == "__main__":
    main()
