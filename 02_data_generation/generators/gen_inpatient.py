#!/usr/bin/env python3
"""
Reference-driven Cerner-like inpatient generator for PostgreSQL (Docker).

Reads hospital structure from cerner_ref:
  - facility

Writes events to cerner:
  - cerner.person
  - cerner.encounter
  - cerner.encntr_loc_hist
  - optionally cerner.order_catalog + cerner.orders (for discharge timing KPIs)

PowerShell run (from D:\\ICDM2026):
  pip install psycopg2-binary
  python ACBP_Clinical_Dashboard_Experiment\\02_data_generation\\generators\\gen_inpatient.py --truncate --days 14 --arrivals_per_day 120 --seed 42 --host 127.0.0.1 --port 55432 --password acbp
"""

import argparse
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional

import psycopg2
from psycopg2.extras import execute_values

UTC = timezone.utc


# -----------------------------
# Helpers
# -----------------------------
def utc_now_floor_minute() -> datetime:
    n = datetime.now(tz=UTC)
    return n.replace(second=0, microsecond=0)


def connect(args):
    return psycopg2.connect(
        host=args.host,
        port=args.port,
        dbname=args.db,
        user=args.user,
        password=args.password,
    )


def bulk_insert(cur, table: str, cols: List[str], rows: List[Tuple], page_size: int = 5000):
    if not rows:
        return
    q = f"INSERT INTO {table} ({', '.join(cols)}) VALUES %s ON CONFLICT DO NOTHING"
    execute_values(cur, q, rows, page_size=page_size)


# -----------------------------
# Minimal CODE_VALUE seeding (synthetic, safe)
# -----------------------------
def ensure_min_code_values(cur):
    """
    Minimal code_value rows used by typical Cerner analytics:
    - sex codes
    - encounter type
    - discharge disposition (incl 'Deceased')
    - plus whatever structure exists in cerner_ref (fac/build/unit/room/bed)
    """
    base_rows = [
        (1001, 1, "MALE", "Male", "Male", 1),
        (1002, 1, "FEMALE", "Female", "Female", 1),
        (2001, 2, "INPATIENT", "Inpatient", "Inpatient", 1),
        (3001, 6, "DECEASED", "Deceased", "Deceased", 1),
        (3002, 6, "HOME", "Home", "Home", 1),
        (3003, 6, "TRANSFER", "Transferred", "Transferred", 1),
    ]

    # ✅ FIX: multi-row insert must use execute_values (not cur.execute with VALUES %s)
    execute_values(
        cur,
        """
        INSERT INTO cerner.code_value
          (code_value, code_set, cdf_meaning, display, description, active_ind)
        VALUES %s
        ON CONFLICT (code_value) DO NOTHING
        """,
        base_rows
    )

    # Structure: push cerner_ref identifiers into code_value (display strings are synthetic)
    cur.execute("""
        INSERT INTO cerner.code_value (code_value, code_set, cdf_meaning, display, description, active_ind)
        SELECT f.facility_cd, 100, 'FACILITY', f.facility_key, 'Facility', 1
        FROM cerner_ref.facility f
        ON CONFLICT (code_value) DO NOTHING;
    """)

    cur.execute("""
        INSERT INTO cerner.code_value (code_value, code_set, cdf_meaning, display, description, active_ind)
        SELECT b.building_cd, 101, 'BUILDING', (f.facility_key || '_' || b.building_type), 'Building', 1
        FROM cerner_ref.building b
        JOIN cerner_ref.facility f ON f.facility_cd = b.facility_cd
        ON CONFLICT (code_value) DO NOTHING;
    """)

    cur.execute("""
        INSERT INTO cerner.code_value (code_value, code_set, cdf_meaning, display, description, active_ind)
        SELECT n.nurse_unit_cd, 102, 'NURSE_UNIT', n.unit_display, 'Nurse Unit', 1
        FROM cerner_ref.nurse_unit n
        ON CONFLICT (code_value) DO NOTHING;
    """)

    cur.execute("""
        INSERT INTO cerner.code_value (code_value, code_set, cdf_meaning, display, description, active_ind)
        SELECT r.room_cd, 103, 'ROOM', ('ROOM_' || r.room_cd::text), 'Room', 1
        FROM cerner_ref.room r
        ON CONFLICT (code_value) DO NOTHING;
    """)

    cur.execute("""
        INSERT INTO cerner.code_value (code_value, code_set, cdf_meaning, display, description, active_ind)
        SELECT b.bed_cd, 104, 'BED', ('BED_' || b.bed_cd::text), 'Bed', 1
        FROM cerner_ref.bed b
        ON CONFLICT (code_value) DO NOTHING;
    """)

    # Procedural pseudo nurse-units (exist in code_value but not in cerner_ref.nurse_unit)
    proc_rows = [
        (925000001, 102, "NURSE_UNIT", "IPD_OR_PROC", "Procedural OR Unit", 1),
        (925000002, 102, "NURSE_UNIT", "IPD_CATH_PROC", "Procedural Cath Unit", 1),
    ]

    # ✅ FIX: also use execute_values here
    execute_values(
        cur,
        """
        INSERT INTO cerner.code_value
          (code_value, code_set, cdf_meaning, display, description, active_ind)
        VALUES %s
        ON CONFLICT (code_value) DO NOTHING
        """,
        proc_rows
    )


# -----------------------------
# Ensure FAC_02..FAC_10 exist (optional)
# -----------------------------
def ensure_other_facilities(cur, seed: int, total_facilities: int = 10):
    """
    If only FAC_01 exists, this will create FAC_02..FAC_10 with small IPD buildings,
    a few nurse units each, capacities, and IPD rooms+beds.
    Names and codes are synthetic and deterministic.
    """
    rng = random.Random(seed)

    for i in range(1, total_facilities + 1):
        fac_key = f"FAC_{i:02d}"
        fac_cd = 900000000 + i

        # if exists, skip
        cur.execute("SELECT 1 FROM cerner_ref.facility WHERE facility_key = %s;", (fac_key,))
        if cur.fetchone():
            continue

        fac_type = "GENERAL" if i != 1 else "CARDIAC_CENTER"
        cur.execute("""
            INSERT INTO cerner_ref.facility (facility_cd, facility_key, facility_type)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (fac_cd, fac_key, fac_type))

        # Buildings: just IPD for other facilities
        bld_ipd = 910000000 + (i * 10) + 2
        cur.execute("""
            INSERT INTO cerner_ref.building (building_cd, facility_cd, building_type)
            VALUES (%s, %s, 'IPD')
            ON CONFLICT DO NOTHING
        """, (bld_ipd, fac_cd))

        # Create 3–6 nurse units with 8–20 beds each
        n_units = rng.randint(3, 6)
        unit_rows = []
        cap_rows = []
        for u in range(n_units):
            nu_cd = 920000000 + (i * 100) + (u + 1)
            pop = "Adult" if rng.random() < 0.85 else "Pediatric"
            fn = rng.choice(["WARD", "CCU", "ICU"])
            floor = rng.choice(["1F", "2F", "3F"])
            unit_key = f"{fac_key}_IPD_U{u+1}"
            unit_display = f"{fac_key} IPD {fn} {floor} U{u+1}"
            unit_rows.append((nu_cd, bld_ipd, unit_key, unit_display, fn, pop, floor))
            beds = rng.randint(8, 20)
            cap_rows.append((nu_cd, beds))

        execute_values(cur, """
            INSERT INTO cerner_ref.nurse_unit
              (nurse_unit_cd, building_cd, unit_key, unit_display, unit_function, population_group, floor_flag)
            VALUES %s
            ON CONFLICT DO NOTHING
        """, unit_rows)

        execute_values(cur, """
            INSERT INTO cerner_ref.unit_capacity (nurse_unit_cd, cap_beds)
            VALUES %s
            ON CONFLICT DO NOTHING
        """, cap_rows)

        # Rooms+beds: one bed per room for simplicity
        room_base = 930000000 + (i * 10000)
        bed_base = 940000000 + (i * 10000)
        room_counter = room_base
        bed_counter = bed_base

        cur.execute(
            "SELECT nurse_unit_cd, cap_beds FROM cerner_ref.unit_capacity WHERE nurse_unit_cd BETWEEN %s AND %s;",
            (920000000 + (i * 100), 920000000 + (i * 100) + 99)
        )
        for (nu_cd, cap) in cur.fetchall():
            for _ in range(cap):
                room_counter += 1
                bed_counter += 1
                cur.execute("""
                    INSERT INTO cerner_ref.room (room_cd, nurse_unit_cd, room_type)
                    VALUES (%s, %s, 'IPD')
                    ON CONFLICT DO NOTHING
                """, (room_counter, nu_cd))
                cur.execute("""
                    INSERT INTO cerner_ref.bed (bed_cd, room_cd)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (bed_counter, room_counter))


def ensure_fac01_or_cath_rooms(cur):
    """
    Ensure a small set of OR and CATH rooms exist for FAC_01.
    These rooms have room_type OR/CATH and NO bed entries.
    """
    proc_rooms = []
    for i in range(1, 5):
        proc_rooms.append((939000000 + i, None, "OR"))
    for i in range(1, 5):
        proc_rooms.append((939000100 + i, None, "CATH"))

    execute_values(cur, """
        INSERT INTO cerner_ref.room (room_cd, nurse_unit_cd, room_type)
        VALUES %s
        ON CONFLICT DO NOTHING
    """, proc_rooms)


def truncate_event_tables(cur):
    cur.execute("TRUNCATE cerner.encntr_loc_hist RESTART IDENTITY CASCADE;")
    cur.execute("TRUNCATE cerner.orders RESTART IDENTITY CASCADE;")
    cur.execute("TRUNCATE cerner.order_catalog RESTART IDENTITY CASCADE;")
    cur.execute("TRUNCATE cerner.encounter RESTART IDENTITY CASCADE;")
    cur.execute("TRUNCATE cerner.person RESTART IDENTITY CASCADE;")


# -----------------------------
# Structure loading
# -----------------------------
def fetch_ipd_beds(cur) -> List[Dict]:
    """
    Returns list of bed records with full location context:
      facility_cd, building_cd, nurse_unit_cd, room_cd, bed_cd
    Only for rooms with room_type='IPD'.
    """
    cur.execute("""
        SELECT
            f.facility_cd, f.facility_key,
            b.building_cd, b.building_type,
            n.nurse_unit_cd, n.unit_display,
            r.room_cd, r.room_type,
            bd.bed_cd
        FROM cerner_ref.bed bd
        JOIN cerner_ref.room r ON r.room_cd = bd.room_cd
        JOIN cerner_ref.nurse_unit n ON n.nurse_unit_cd = r.nurse_unit_cd
        JOIN cerner_ref.building b ON b.building_cd = n.building_cd
        JOIN cerner_ref.facility f ON f.facility_cd = b.facility_cd
        WHERE r.room_type = 'IPD'
          AND n.active_ind = 1 AND b.active_ind = 1 AND f.active_ind = 1
        ORDER BY f.facility_key, n.nurse_unit_cd, r.room_cd
    """)
    beds = []
    for row in cur.fetchall():
        beds.append({
            "facility_cd": row[0],
            "facility_key": row[1],
            "building_cd": row[2],
            "building_type": row[3],
            "nurse_unit_cd": row[4],
            "nurse_unit_display": row[5],
            "room_cd": row[6],
            "room_type": row[7],
            "bed_cd": row[8],
        })
    return beds


def fetch_proc_rooms(cur) -> Dict[str, List[int]]:
    cur.execute("""
        SELECT room_type, room_cd
        FROM cerner_ref.room
        WHERE room_type IN ('OR', 'CATH')
        ORDER BY room_type, room_cd
    """)
    out = {"OR": [], "CATH": []}
    for t, room_cd in cur.fetchall():
        out[t].append(room_cd)
    return out


# -----------------------------
# Data generation
# -----------------------------
def gen_people(seed: int, n_people: int, start_person_id: int) -> List[Tuple]:
    rng = random.Random(seed)
    rows = []
    now = utc_now_floor_minute()
    for i in range(n_people):
        pid = start_person_id + i
        sex_cd = 1001 if rng.random() < 0.55 else 1002
        age_years = rng.randint(1, 90)
        birth = now - timedelta(days=int(age_years * 365.25))
        name = f"PATIENT_{pid}"
        rows.append((pid, name, birth, None, sex_cd, None, 1))
    return rows


def gen_encounters(seed: int,
                   people_ids: List[int],
                   start_encntr_id: int,
                   start_ts: datetime,
                   end_ts: datetime,
                   arrivals_per_day: int,
                   p_open: float,
                   p_fac01: float,
                   facility_keys: List[str],
                   fac_key_to_cd: Dict[str, int]) -> List[Dict]:
    rng = random.Random(seed)

    total_days = max(1, int((end_ts - start_ts).total_seconds() // 86400))
    total_arrivals = arrivals_per_day * total_days

    encntr_id = start_encntr_id
    encs = []

    others = [k for k in facility_keys if k != "FAC_01"]
    for _ in range(total_arrivals):
        pid = rng.choice(people_ids)

        admit_offset = rng.random() * (end_ts - start_ts).total_seconds()
        admit = start_ts + timedelta(seconds=admit_offset)
        admit = admit.replace(second=0, microsecond=0)

        x = rng.random()
        if x < 0.70:
            los_hours = rng.randint(12, 72)
        elif x < 0.90:
            los_hours = rng.randint(72, 240)
        else:
            los_hours = rng.randint(240, 720)

        disch = admit + timedelta(hours=los_hours)
        if rng.random() < p_open or (disch > end_ts and rng.random() < 0.60):
            disch = None

        if rng.random() < p_fac01 or not others:
            fac_key = "FAC_01"
        else:
            fac_key = rng.choice(others)

        encs.append({
            "encntr_id": encntr_id,
            "person_id": pid,
            "encntr_type_cd": 2001,
            "facility_key": fac_key,
            "facility_cd": fac_key_to_cd[fac_key],
            "reg_dt_tm": admit - timedelta(minutes=rng.randint(5, 180)),
            "inpatient_admit_dt_tm": admit,
            "disch_dt_tm": disch,
            "est_depart_dt_tm": disch,
            "active_ind": 1
        })
        encntr_id += 1

    encs.sort(key=lambda e: e["inpatient_admit_dt_tm"])
    return encs


def assign_locations_and_events(seed: int,
                               encounters: List[Dict],
                               ipd_beds: List[Dict],
                               proc_rooms: Dict[str, List[int]],
                               end_ts: datetime,
                               transfer_rate_per_day: float,
                               p_cross_fac_transfer: float,
                               p_procedure: float,
                               p_or_vs_cath: float) -> Tuple[List[Tuple], Dict[int, Tuple]]:
    rng = random.Random(seed)

    bed_state: Dict[int, Tuple[int, datetime]] = {}
    beds_by_fac: Dict[int, List[Dict]] = {}
    for b in ipd_beds:
        beds_by_fac.setdefault(b["facility_cd"], []).append(b)

    elh_rows: List[Tuple] = []
    current_loc: Dict[int, Tuple] = {}

    def release_expired(at: datetime):
        expired = [bed for bed, (_, until) in bed_state.items() if until <= at]
        for bed in expired:
            bed_state.pop(bed, None)

    def find_free_bed(facility_cd: int, at: datetime) -> Optional[Dict]:
        release_expired(at)
        candidates = beds_by_fac.get(facility_cd, [])
        free = [b for b in candidates if b["bed_cd"] not in bed_state]
        if not free:
            return None
        return rng.choice(free)

    all_facs = sorted(beds_by_fac.keys())

    for e in encounters:
        encntr_id = e["encntr_id"]
        admit = e["inpatient_admit_dt_tm"]
        disch = e["disch_dt_tm"] or end_ts
        facility_cd = e["facility_cd"]

        b0 = find_free_bed(facility_cd, admit)
        if b0 is None:
            continue

        bed_state[b0["bed_cd"]] = (encntr_id, disch)
        current_loc[encntr_id] = (b0["facility_cd"], b0["building_cd"], b0["nurse_unit_cd"], b0["room_cd"], b0["bed_cd"])

        elh_rows.append((
            encntr_id,
            b0["facility_cd"], b0["building_cd"], b0["nurse_unit_cd"], b0["room_cd"], b0["bed_cd"],
            admit, None, admit, 1
        ))

        stay_days = max(0.01, (disch - admit).total_seconds() / 86400.0)
        expected_transfers = stay_days * transfer_rate_per_day
        n_transfers = min(int(expected_transfers + rng.random()), 6)

        transfer_times = sorted([
            admit + timedelta(seconds=rng.random() * (disch - admit).total_seconds())
            for _ in range(n_transfers)
        ])
        transfer_times = [t.replace(second=0, microsecond=0) for t in transfer_times]
        transfer_times = [t for t in transfer_times if admit + timedelta(minutes=60) < t < disch - timedelta(minutes=60)]

        proc_time = None
        proc_kind = None
        if proc_rooms["OR"] and proc_rooms["CATH"] and rng.random() < p_procedure and (disch - admit) > timedelta(hours=6):
            proc_time = admit + timedelta(seconds=rng.random() * (disch - admit).total_seconds())
            proc_time = proc_time.replace(second=0, microsecond=0)
            if admit + timedelta(hours=2) < proc_time < disch - timedelta(hours=2):
                proc_kind = "OR" if rng.random() < p_or_vs_cath else "CATH"
            else:
                proc_time = None
                proc_kind = None

        events = [{"t": t, "type": "XFER"} for t in transfer_times]
        if proc_time is not None:
            events.append({"t": proc_time, "type": proc_kind})
        events.sort(key=lambda x: x["t"])

        for ev in events:
            t = ev["t"]

            # close current open segment
            for idx in range(len(elh_rows) - 1, -1, -1):
                if elh_rows[idx][0] == encntr_id and elh_rows[idx][7] is None:
                    prev = list(elh_rows[idx])
                    prev[7] = t
                    elh_rows[idx] = tuple(prev)
                    break

            cur_fac, cur_bld, cur_nu, cur_room, cur_bed = current_loc[encntr_id]
            if cur_bed is not None:
                bed_state.pop(cur_bed, None)

            if ev["type"] in ("OR", "CATH"):
                proc_room = rng.choice(proc_rooms[ev["type"]])
                proc_nu = 925000001 if ev["type"] == "OR" else 925000002
                dur = timedelta(minutes=rng.randint(60, 240))
                endp = min(disch, t + dur)

                elh_rows.append((
                    encntr_id,
                    cur_fac, cur_bld, proc_nu, proc_room, None,
                    t, endp, t, 1
                ))

                b1 = find_free_bed(cur_fac, endp)
                if b1 is None:
                    b1 = {"facility_cd": cur_fac, "building_cd": cur_bld, "nurse_unit_cd": cur_nu, "room_cd": cur_room, "bed_cd": cur_bed}

                bed_state[b1["bed_cd"]] = (encntr_id, disch)
                current_loc[encntr_id] = (b1["facility_cd"], b1["building_cd"], b1["nurse_unit_cd"], b1["room_cd"], b1["bed_cd"])
                elh_rows.append((
                    encntr_id,
                    b1["facility_cd"], b1["building_cd"], b1["nurse_unit_cd"], b1["room_cd"], b1["bed_cd"],
                    endp, None, endp, 1
                ))
                continue

            new_fac = cur_fac
            if rng.random() < p_cross_fac_transfer and len(all_facs) > 1:
                new_fac = rng.choice([f for f in all_facs if f != cur_fac])

            b2 = find_free_bed(new_fac, t) or find_free_bed(cur_fac, t)
            if b2 is None:
                b2 = {"facility_cd": cur_fac, "building_cd": cur_bld, "nurse_unit_cd": cur_nu, "room_cd": cur_room, "bed_cd": cur_bed}

            bed_state[b2["bed_cd"]] = (encntr_id, disch)
            current_loc[encntr_id] = (b2["facility_cd"], b2["building_cd"], b2["nurse_unit_cd"], b2["room_cd"], b2["bed_cd"])
            elh_rows.append((
                encntr_id,
                b2["facility_cd"], b2["building_cd"], b2["nurse_unit_cd"], b2["room_cd"], b2["bed_cd"],
                t, None, t, 1
            ))

        if e["disch_dt_tm"] is not None:
            disch_real = e["disch_dt_tm"]
            for idx in range(len(elh_rows) - 1, -1, -1):
                if elh_rows[idx][0] == encntr_id and elh_rows[idx][7] is None:
                    prev = list(elh_rows[idx])
                    prev[7] = disch_real
                    elh_rows[idx] = tuple(prev)
                    break

            _, _, _, _, cur_bed = current_loc.get(encntr_id, (None, None, None, None, None))
            if cur_bed is not None:
                bed_state.pop(cur_bed, None)

    return elh_rows, current_loc


def update_encounter_current_loc(cur, loc_map: Dict[int, Tuple]):
    rows = [(fac, bld, nu, room, bed, encntr_id) for encntr_id, (fac, bld, nu, room, bed) in loc_map.items()]
    if not rows:
        return
    execute_values(cur, """
        UPDATE cerner.encounter e SET
            loc_facility_cd = v.facility_cd,
            loc_building_cd = v.building_cd,
            loc_nurse_unit_cd = v.nurse_unit_cd,
            loc_room_cd = v.room_cd,
            loc_bed_cd = v.bed_cd,
            updated_at = now()
        FROM (VALUES %s) AS v(facility_cd, building_cd, nurse_unit_cd, room_cd, bed_cd, encntr_id)
        WHERE e.encntr_id = v.encntr_id
    """, rows, page_size=5000)


def ensure_discharge_catalog(cur):
    rows = [
        (1111, 636727, "Discharge Patient", "Discharge Patient"),
        (1112, 636727, "Request for Admit", "Request for Admit"),
    ]
    execute_values(cur, """
        INSERT INTO cerner.order_catalog (catalog_cd, catalog_type_cd, primary_mnemonic, description)
        VALUES %s
        ON CONFLICT DO NOTHING
    """, rows)


def gen_discharge_orders(seed: int, encounters: List[Dict], p_discharge_order: float) -> List[Tuple]:
    rng = random.Random(seed)
    orders = []
    order_id = 88000000
    for e in encounters:
        if e["disch_dt_tm"] is None:
            continue
        if rng.random() > p_discharge_order:
            continue
        disch = e["disch_dt_tm"]
        placed = disch - timedelta(hours=rng.randint(1, 24))
        orders.append((
            order_id,
            e["encntr_id"],
            1111,
            636727,
            placed,
            "Discharge Patient",
            0,
            None,
            1
        ))
        order_id += 1
    return orders


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", default=5432, type=int)
    ap.add_argument("--db", default="acbp_db")
    ap.add_argument("--user", default="acbp")
    ap.add_argument("--password", default="acbp")

    ap.add_argument("--seed", default=42, type=int)
    ap.add_argument("--days", default=14, type=int)
    ap.add_argument("--arrivals_per_day", default=120, type=int)
    ap.add_argument("--p_open", default=0.25, type=float)

    ap.add_argument("--ensure_facilities", default=10, type=int)
    ap.add_argument("--p_fac01", default=0.70, type=float)

    ap.add_argument("--transfer_rate_per_day", default=0.40, type=float)
    ap.add_argument("--p_cross_fac_transfer", default=0.03, type=float)

    ap.add_argument("--p_procedure", default=0.12, type=float)
    ap.add_argument("--p_or_vs_cath", default=0.55, type=float)

    ap.add_argument("--p_discharge_order", default=0.60, type=float)
    ap.add_argument("--truncate", action="store_true")
    args = ap.parse_args()

    start_ts = utc_now_floor_minute() - timedelta(days=args.days)
    end_ts = utc_now_floor_minute()

    conn = connect(args)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            if args.truncate:
                truncate_event_tables(cur)

            ensure_other_facilities(cur, seed=args.seed + 10, total_facilities=args.ensure_facilities)
            ensure_fac01_or_cath_rooms(cur)
            ensure_min_code_values(cur)

            # ✅ FIX: correct dict mapping
            cur.execute("SELECT facility_key, facility_cd FROM cerner_ref.facility WHERE active_ind=1 ORDER BY facility_key;")
            fac_rows = cur.fetchall()
            facility_keys = [r[0] for r in fac_rows]
            fac_key_to_cd = {r[0]: r[1] for r in fac_rows}

            ipd_beds = fetch_ipd_beds(cur)
            if not ipd_beds:
                raise RuntimeError("No IPD beds found in cerner_ref. Seed FAC_01 first (and/or ensure_other_facilities).")

            proc_rooms = fetch_proc_rooms(cur)

            n_people = args.arrivals_per_day * args.days
            people_rows = gen_people(args.seed + 1, n_people=n_people, start_person_id=5000000)
            bulk_insert(
                cur,
                "cerner.person",
                ["person_id","name_full_formatted","birth_dt_tm","deceased_dt_tm","sex_cd","nationality_cd","active_ind"],
                people_rows
            )
            people_ids = [r[0] for r in people_rows]

            encounters = gen_encounters(
                seed=args.seed + 2,
                people_ids=people_ids,
                start_encntr_id=70000000,
                start_ts=start_ts,
                end_ts=end_ts,
                arrivals_per_day=args.arrivals_per_day,
                p_open=args.p_open,
                p_fac01=args.p_fac01,
                facility_keys=facility_keys,
                fac_key_to_cd=fac_key_to_cd
            )

            enc_rows = []
            for e in encounters:
                enc_rows.append((
                    e["encntr_id"], e["person_id"],
                    e["encntr_type_cd"], None, None, None, None, None, None,
                    e["facility_cd"], None, None, None, None,
                    e["reg_dt_tm"], e["inpatient_admit_dt_tm"], e["disch_dt_tm"], e["est_depart_dt_tm"],
                    e["active_ind"]
                ))

            bulk_insert(
                cur,
                "cerner.encounter",
                [
                    "encntr_id","person_id",
                    "encntr_type_cd","encntr_status_cd","med_service_cd","service_category_cd","isolation_cd","vip_cd","disch_disposition_cd",
                    "loc_facility_cd","loc_building_cd","loc_nurse_unit_cd","loc_room_cd","loc_bed_cd",
                    "reg_dt_tm","inpatient_admit_dt_tm","disch_dt_tm","est_depart_dt_tm",
                    "active_ind"
                ],
                enc_rows
            )

            elh_rows, loc_map = assign_locations_and_events(
                seed=args.seed + 3,
                encounters=encounters,
                ipd_beds=ipd_beds,
                proc_rooms=proc_rooms,
                end_ts=end_ts,
                transfer_rate_per_day=args.transfer_rate_per_day,
                p_cross_fac_transfer=args.p_cross_fac_transfer,
                p_procedure=args.p_procedure,
                p_or_vs_cath=args.p_or_vs_cath
            )

            bulk_insert(
                cur,
                "cerner.encntr_loc_hist",
                [
                    "encntr_id","loc_facility_cd","loc_building_cd","loc_nurse_unit_cd","loc_room_cd","loc_bed_cd",
                    "beg_effective_dt_tm","end_effective_dt_tm","transaction_dt_tm","active_ind"
                ],
                elh_rows
            )

            update_encounter_current_loc(cur, loc_map)

            ensure_discharge_catalog(cur)
            order_rows = gen_discharge_orders(args.seed + 4, encounters, args.p_discharge_order)
            bulk_insert(
                cur,
                "cerner.orders",
                ["order_id","encntr_id","catalog_cd","catalog_type_cd","orig_order_dt_tm","hna_order_mnemonic","product_id","order_status_cd","active_ind"],
                order_rows
            )

        conn.commit()
        print("✅ Generated synthetic inpatient events (reference-driven).")
        print(f"   Encounters generated: {len(encounters)}")
        print(f"   ENCNTR_LOC_HIST rows: {len(elh_rows)}")
        print(f"   Discharge orders: {len(order_rows)}")
        print(f"   Horizon: {start_ts.isoformat()} → {end_ts.isoformat()}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()