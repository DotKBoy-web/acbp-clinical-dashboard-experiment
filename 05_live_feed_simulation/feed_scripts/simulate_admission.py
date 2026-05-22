#!/usr/bin/env python3
"""
simulate_admission.py
Add N new inpatient encounters into FAC_01 IPD.
If no free beds exist, optionally admit as "unbedded" (room/bed NULL) to keep flow realistic.
"""

import argparse
import random
from datetime import datetime, timedelta, timezone

import psycopg2
from psycopg2.extras import execute_values

UTC = timezone.utc


def now_utc_floor_min():
    t = datetime.now(tz=UTC)
    return t.replace(second=0, microsecond=0)


def connect(args):
    return psycopg2.connect(
        host=args.host,
        port=args.port,
        dbname=args.db,
        user=args.user,
        password=args.password,
    )


def get_next_ids(cur, n: int):
    cur.execute("SELECT COALESCE(MAX(person_id), 5000000) FROM cerner.person;")
    max_person = cur.fetchone()[0] or 5000000
    cur.execute("SELECT COALESCE(MAX(encntr_id), 70000000) FROM cerner.encounter;")
    max_enc = cur.fetchone()[0] or 70000000
    return max_person + 1, max_enc + 1


def fetch_free_beds_fac01(cur, limit: int):
    cur.execute(
        """
        WITH fac01_ipd_beds AS (
          SELECT f.facility_cd, b.building_cd, nu.nurse_unit_cd, r.room_cd, bd.bed_cd
          FROM cerner_ref.bed bd
          JOIN cerner_ref.room r ON r.room_cd = bd.room_cd AND r.room_type = 'IPD'
          JOIN cerner_ref.nurse_unit nu ON nu.nurse_unit_cd = r.nurse_unit_cd
          JOIN cerner_ref.building b ON b.building_cd = nu.building_cd AND b.building_type = 'IPD'
          JOIN cerner_ref.facility f ON f.facility_cd = b.facility_cd AND f.facility_key = 'FAC_01'
        ),
        occupied_now AS (
          SELECT DISTINCT e.loc_bed_cd AS bed_cd
          FROM cerner.encounter e
          WHERE e.active_ind = 1
            AND e.inpatient_admit_dt_tm IS NOT NULL
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


def fetch_any_units_fac01(cur, limit: int):
    cur.execute(
        """
        SELECT nu.nurse_unit_cd, b.building_cd, f.facility_cd
        FROM cerner_ref.nurse_unit nu
        JOIN cerner_ref.building b ON b.building_cd = nu.building_cd AND b.building_type='IPD'
        JOIN cerner_ref.facility f ON f.facility_cd = b.facility_cd AND f.facility_key='FAC_01'
        WHERE nu.active_ind=1
        ORDER BY random()
        LIMIT %s;
        """,
        (limit,),
    )
    return cur.fetchall()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)

    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=55432)
    ap.add_argument("--db", default="acbp_db")
    ap.add_argument("--user", default="acbp")
    ap.add_argument("--password", default="acbp")

    ap.add_argument("--encntr_type_cd", type=int, default=2001)
    ap.add_argument("--p_male", type=float, default=0.55)
    ap.add_argument("--min_age", type=int, default=1)
    ap.add_argument("--max_age", type=int, default=90)

    ap.add_argument("--allow_unbedded", action="store_true",
                    help="If no free beds exist, admit with NULL room/bed in a valid unit.")

    args = ap.parse_args()
    rng = random.Random(args.seed)
    t0 = now_utc_floor_min()

    conn = connect(args)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            free_beds = fetch_free_beds_fac01(cur, args.n)

            # If no beds available, optionally admit as unbedded
            unbedded_units = []
            if not free_beds and args.allow_unbedded:
                unbedded_units = fetch_any_units_fac01(cur, args.n)

            if not free_beds and not unbedded_units:
                print("No free beds available in FAC_01 IPD. 0 admissions inserted.")
                conn.rollback()
                return

            n_actual = min(args.n, len(free_beds) + len(unbedded_units))
            next_person_id, next_encntr_id = get_next_ids(cur, n_actual)

            # Persons
            person_rows = []
            for i in range(n_actual):
                pid = next_person_id + i
                sex_cd = 1001 if rng.random() < args.p_male else 1002
                age_years = rng.randint(args.min_age, args.max_age)
                birth = t0 - timedelta(days=int(age_years * 365.25))
                name = f"PATIENT_{pid}"
                person_rows.append((pid, name, birth, None, sex_cd, None, 1))

            execute_values(
                cur,
                """
                INSERT INTO cerner.person
                  (person_id, name_full_formatted, birth_dt_tm, deceased_dt_tm, sex_cd, nationality_cd, active_ind)
                VALUES %s
                ON CONFLICT DO NOTHING
                """,
                person_rows
            )

            enc_rows = []
            elh_rows = []

            # Assign beds first, then unbedded
            assignments = []
            assignments.extend([("bedded", row) for row in free_beds])
            assignments.extend([("unbedded", row) for row in unbedded_units])
            assignments = assignments[:n_actual]

            for i in range(n_actual):
                pid = next_person_id + i
                encntr_id = next_encntr_id + i
                kind, row = assignments[i]

                if kind == "bedded":
                    facility_cd, building_cd, nurse_unit_cd, room_cd, bed_cd = row
                else:
                    nurse_unit_cd, building_cd, facility_cd = row
                    room_cd, bed_cd = None, None

                admit = t0 + timedelta(minutes=rng.randint(-60, 0))
                reg = admit - timedelta(minutes=rng.randint(5, 180))

                enc_rows.append((
                    encntr_id, pid,
                    args.encntr_type_cd,
                    None, None, None, None, None, None,
                    facility_cd, building_cd, nurse_unit_cd, room_cd, bed_cd,
                    reg, admit, None, None,
                    1
                ))

                elh_rows.append((
                    encntr_id,
                    facility_cd, building_cd, nurse_unit_cd, room_cd, bed_cd,
                    admit, None, admit, 1
                ))

            execute_values(
                cur,
                """
                INSERT INTO cerner.encounter
                  (encntr_id, person_id,
                   encntr_type_cd, encntr_status_cd, med_service_cd, service_category_cd, isolation_cd, vip_cd, disch_disposition_cd,
                   loc_facility_cd, loc_building_cd, loc_nurse_unit_cd, loc_room_cd, loc_bed_cd,
                   reg_dt_tm, inpatient_admit_dt_tm, disch_dt_tm, est_depart_dt_tm,
                   active_ind)
                VALUES %s
                ON CONFLICT DO NOTHING
                """,
                enc_rows
            )

            execute_values(
                cur,
                """
                INSERT INTO cerner.encntr_loc_hist
                  (encntr_id, loc_facility_cd, loc_building_cd, loc_nurse_unit_cd, loc_room_cd, loc_bed_cd,
                   beg_effective_dt_tm, end_effective_dt_tm, transaction_dt_tm, active_ind)
                VALUES %s
                """,
                elh_rows
            )

        conn.commit()
        print(f"Inserted admissions: {n_actual} (requested {args.n}).")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
