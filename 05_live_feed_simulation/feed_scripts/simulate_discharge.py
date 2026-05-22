#!/usr/bin/env python3
"""
simulate_discharge.py
Discharge K open encounters in FAC_01 IPD and close their last ENCNTR_LOC_HIST segment.
"""

import argparse
from datetime import datetime, timezone
import psycopg2

UTC = timezone.utc


def now_utc_floor_min():
    t = datetime.now(tz=UTC)
    return t.replace(second=0, microsecond=0)


def connect(args):
    return psycopg2.connect(host=args.host, port=args.port, dbname=args.db, user=args.user, password=args.password)


def fetch_open_encounters_fac01(cur, k: int):
    cur.execute(
        """
        SELECT e.encntr_id
        FROM cerner.encounter e
        JOIN cerner_ref.nurse_unit nu ON nu.nurse_unit_cd = e.loc_nurse_unit_cd
        JOIN cerner_ref.building b ON b.building_cd = nu.building_cd AND b.building_type='IPD'
        JOIN cerner_ref.facility f ON f.facility_cd = b.facility_cd AND f.facility_key='FAC_01'
        WHERE e.active_ind=1
          AND e.inpatient_admit_dt_tm IS NOT NULL
          AND (e.disch_dt_tm IS NULL OR e.disch_dt_tm > now())
        ORDER BY random()
        LIMIT %s;
        """,
        (k,),
    )
    return [r[0] for r in cur.fetchall()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=55432)
    ap.add_argument("--db", default="acbp_db")
    ap.add_argument("--user", default="acbp")
    ap.add_argument("--password", default="acbp")
    args = ap.parse_args()

    t = now_utc_floor_min()
    conn = connect(args)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            encntr_ids = fetch_open_encounters_fac01(cur, args.k)
            if not encntr_ids:
                print("No open encounters found to discharge.")
                conn.rollback()
                return

            cur.execute(
                """
                UPDATE cerner.encounter
                SET disch_dt_tm = %s,
                    est_depart_dt_tm = %s,
                    updated_at = now()
                WHERE encntr_id = ANY(%s);
                """,
                (t, t, encntr_ids),
            )

            cur.execute(
                """
                UPDATE cerner.encntr_loc_hist
                SET end_effective_dt_tm = %s
                WHERE encntr_id = ANY(%s)
                  AND end_effective_dt_tm IS NULL
                  AND active_ind = 1;
                """,
                (t, encntr_ids),
            )

        conn.commit()
        print(f"Discharged encounters: {len(encntr_ids)} (requested {args.k}).")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()