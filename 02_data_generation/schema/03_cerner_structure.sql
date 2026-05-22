/* ============================================================================
   Cerner-like STRUCTURAL REFERENCE LAYER
   Additive schema – does NOT modify transactional tables
   ============================================================================ */

CREATE SCHEMA IF NOT EXISTS cerner_ref;

-- ============================================================================
-- FACILITY
-- ============================================================================

CREATE TABLE IF NOT EXISTS cerner_ref.facility (
    facility_cd    BIGINT PRIMARY KEY,
    facility_key   TEXT UNIQUE NOT NULL,     -- FAC_01 … FAC_10
    facility_type  TEXT NOT NULL,             -- CARDIAC_CENTER, GENERAL
    active_ind     SMALLINT DEFAULT 1
);

-- ============================================================================
-- BUILDING (OPD / IPD separation)
-- ============================================================================

CREATE TABLE IF NOT EXISTS cerner_ref.building (
    building_cd    BIGINT PRIMARY KEY,
    facility_cd    BIGINT NOT NULL
        REFERENCES cerner_ref.facility(facility_cd),
    building_type  TEXT NOT NULL,             -- OPD, IPD
    active_ind     SMALLINT DEFAULT 1
);

CREATE INDEX IF NOT EXISTS ix_building_facility
    ON cerner_ref.building (facility_cd);

-- ============================================================================
-- NURSE UNIT (CORE OF INPATIENT KPIs)
-- ============================================================================

CREATE TABLE IF NOT EXISTS cerner_ref.nurse_unit (
    nurse_unit_cd     BIGINT PRIMARY KEY,
    building_cd       BIGINT NOT NULL
        REFERENCES cerner_ref.building(building_cd),

    unit_key          TEXT NOT NULL,           -- synthetic stable key
    unit_display      TEXT NOT NULL,           -- anonymized name
    unit_function     TEXT NOT NULL,           -- ICU, CCU, WARD, AFTER_SURGERY
    population_group  TEXT NOT NULL,           -- Adult, Pediatric
    floor_flag        TEXT,                    -- GF, 1F, 2F, 3F

    active_ind        SMALLINT DEFAULT 1
);

CREATE INDEX IF NOT EXISTS ix_nurse_unit_building
    ON cerner_ref.nurse_unit (building_cd);

-- ============================================================================
-- UNIT CAPACITY (REPLACES hard-coded unit_capacity CTEs)
-- ============================================================================

CREATE TABLE IF NOT EXISTS cerner_ref.unit_capacity (
    nurse_unit_cd   BIGINT PRIMARY KEY
        REFERENCES cerner_ref.nurse_unit(nurse_unit_cd),
    cap_beds        INTEGER NOT NULL CHECK (cap_beds > 0),
    active_ind      SMALLINT DEFAULT 1
);

-- ============================================================================
-- ROOMS (IPD / OR / CATH / PACU)
-- ============================================================================

CREATE TABLE IF NOT EXISTS cerner_ref.room (
    room_cd        BIGINT PRIMARY KEY,
    nurse_unit_cd  BIGINT
        REFERENCES cerner_ref.nurse_unit(nurse_unit_cd),
    room_type      TEXT NOT NULL,              -- IPD, OR, CATH, PACU
    active_ind     SMALLINT DEFAULT 1
);

CREATE INDEX IF NOT EXISTS ix_room_nurse_unit
    ON cerner_ref.room (nurse_unit_cd);

-- ============================================================================
-- BEDS
-- ============================================================================

CREATE TABLE IF NOT EXISTS cerner_ref.bed (
    bed_cd      BIGINT PRIMARY KEY,
    room_cd     BIGINT NOT NULL
        REFERENCES cerner_ref.room(room_cd),
    active_ind  SMALLINT DEFAULT 1
);

CREATE INDEX IF NOT EXISTS ix_bed_room
    ON cerner_ref.bed (room_cd);

-- ============================================================================
-- OPTIONAL PERFORMANCE INDEXES ON TRANSACTIONAL TABLES
-- (safe, additive, helps later queries)
-- ============================================================================

CREATE INDEX IF NOT EXISTS ix_encounter_fac_bldg
    ON cerner.encounter (loc_facility_cd, loc_building_cd);

CREATE INDEX IF NOT EXISTS ix_elh_fac_bldg
    ON cerner.encntr_loc_hist (loc_facility_cd, loc_building_cd);