#!/usr/bin/env python3
"""
simulate_transfer.py
Move up to K open bedded encounters in FAC_01 IPD to new free beds,
closing previous ENCNTR_LOC_HIST segment and inserting a new one.
"""

import argparse
import random
from datetime import datetime, timezone
import psycopg2
from psycopg2.extras import execute_values

UTC = timezone.utc


def now_utc_floor_min():
    t = datetime.now(tz=UTC)
    return t.replace(second=0, microsecond=0)


def connect(args):
    return psycopg2.connect(host=args.host, port=args.port, dbname=args.db, user=args.user, password=args.password)


def fetch_open_bedded_fac01(cur, k):
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
          AND e.loc_bed_cd IS NOT NULL
        ORDER BY random()
        LIMIT %s;
        """,
        (k,),
    )
    return [r[0] for r in cur.fetchall()]


def fetch_free_beds_fac01(cur, limit):
    cur.execute(
        """
        WITH fac01_ipd_beds AS (
          SELECT f.facility_cd, b.building_cd, nu.nurse_unit_cd, r.room_cd, bd.bed_cd
          FROM cerner_ref.bed bd
          JOIN cerner_ref.room r ON r.room_cd = bd.room_cd AND r.room_type='IPD'
          JOIN cerner_ref.nurse_unit nu ON nu.nurse_unit_cd = r.nurse_unit_cd
          JOIN cerner_ref.building b ON b.building_cd = nu.building_cd AND b.building_type='IPD'
          JOIN cerner_ref.facility f ON f.facility_cd=b.facility_cd AND f.facility_key='FAC_01'
        ),
        occupied_now AS (
          SELECT DISTINCT e.loc_bed_cd AS bed_cd
          FROM cerner.encounter e
          WHERE e.active_ind=1
            AND e.loc_bed_cd IS NOT NULL
            AND (e.disch_dt_tm IS NULL OR e.disch_dt_tm > now())
        )
        SELECT fb.facility_cd, fb.building_cd, fb.nurse_unit_cd, fb.room_cd, fb.bed_cd
        FROM fac01_ipd_beds fb
        LEFT JOIN occupied_now o ON o.bed_cd = fb.bed_cd
        WHERE o.bed_cd IS NULL
        ORDER BY random()
        LIMIT %s;
        """,
        (limit,),
    )
    return cur.fetchall()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--transfer_probability", type=float, default=0.6)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=55432)
    ap.add_argument("--db", default="acbp_db")
    ap.add_argument("--user", default="acbp")
    ap.add_argument("--password", default="acbp")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    t = now_utc_floor_min()

    conn = connect(args)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            candidates = fetch_open_bedded_fac01(cur, args.k)
            # probabilistic selection
            chosen = [eid for eid in candidates if rng.random() < args.transfer_probability]
            if not chosen:
                print("No encounters selected for transfer (probability filter).")
                conn.rollback()
                return

            free_beds = fetch_free_beds_fac01(cur, len(chosen))
            if not free_beds:
                print("No free beds available for transfer.")
                conn.rollback()
                return

            n = min(len(chosen), len(free_beds))
            chosen = chosen[:n]
            targets = free_beds[:n]

            # close previous ELH segments
            cur.execute(
                """
                UPDATE cerner.encntr_loc_hist
                SET end_effective_dt_tm = %s
                WHERE encntr_id = ANY(%s)
                  AND end_effective_dt_tm IS NULL
                  AND active_ind = 1;
                """,
                (t, chosen),
            )

            enc_updates = []
            elh_inserts = []

            for i in range(n):
                eid = chosen[i]
                fac, bld, nu, room, bed = targets[i]
                enc_updates.append((fac, bld, nu, room, bed, eid))
                elh_inserts.append((eid, fac, bld, nu, room, bed, t, None, t, 1))

            execute_values(
                cur,
                """
                UPDATE cerner.encounter e SET
                  loc_facility_cd = v.facility_cd,
                  loc_building_cd = v.building_cd,
                  loc_nurse_unit_cd = v.nurse_unit_cd,
                  loc_room_cd = v.room_cd,
                  loc_bed_cd = v.bed_cd,
                  updated_at = now()
                FROM (VALUES %s) AS v(facility_cd, building_cd, nurse_unit_cd, room_cd, bed_cd, encntr_id)
                WHERE e.encntr_id = v.encntr_id;
                """,
                enc_updates,
                page_size=1000
            )

            execute_values(
                cur,
                """
                INSERT INTO cerner.encntr_loc_hist
                  (encntr_id, loc_facility_cd, loc_building_cd, loc_nurse_unit_cd, loc_room_cd, loc_bed_cd,
                   beg_effective_dt_tm, end_effective_dt_tm, transaction_dt_tm, active_ind)
                VALUES %s;
                """,
                elh_inserts,
                page_size=1000
            )

        conn.commit()
        print(f"Transferred encounters: {n} (requested {args.k}).")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()