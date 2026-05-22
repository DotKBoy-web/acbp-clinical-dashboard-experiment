-- 02_data_generation/schema/02_cerner_inpatient_ops.sql
-- Cerner-shaped inpatient encounter + location history schema.
-- Focus: ENCOUNTER + ENCNTR_LOC_HIST + minimal operational adjuncts.

CREATE SCHEMA IF NOT EXISTS cerner;

-- -----------------------------
-- ENCOUNTER (Millennium-style)
-- -----------------------------
CREATE TABLE IF NOT EXISTS cerner.encounter (
    encntr_id               BIGINT PRIMARY KEY,
    person_id               BIGINT NOT NULL REFERENCES cerner.person(person_id),

    -- Encounter descriptors (coded)
    encntr_type_cd          BIGINT,   -- e.g., Inpatient
    encntr_status_cd        BIGINT,
    med_service_cd          BIGINT,
    service_category_cd     BIGINT,
    isolation_cd            BIGINT,
    vip_cd                  BIGINT,
    disch_disposition_cd    BIGINT,

    -- Current location (coded) - Cerner-style columns
    loc_facility_cd         BIGINT,
    loc_building_cd         BIGINT,
    loc_nurse_unit_cd       BIGINT,
    loc_room_cd             BIGINT,
    loc_bed_cd              BIGINT,

    -- Time columns (UTC recommended; your app can treat as GMT)
    reg_dt_tm               TIMESTAMPTZ,
    inpatient_admit_dt_tm   TIMESTAMPTZ,
    disch_dt_tm             TIMESTAMPTZ,
    est_depart_dt_tm        TIMESTAMPTZ,

    active_ind              SMALLINT NOT NULL DEFAULT 1,

    -- Optional: denormalized convenience for experiments
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_encounter_active_inpatient_admit
    ON cerner.encounter (active_ind, inpatient_admit_dt_tm);

CREATE INDEX IF NOT EXISTS ix_encounter_current_loc
    ON cerner.encounter (loc_facility_cd, loc_building_cd, loc_nurse_unit_cd, loc_room_cd, loc_bed_cd);

-- -----------------------------
-- ENCNTR_LOC_HIST (Millennium-style location history)
-- -----------------------------
CREATE TABLE IF NOT EXISTS cerner.encntr_loc_hist (
    encntr_loc_hist_id     BIGSERIAL PRIMARY KEY,
    encntr_id              BIGINT NOT NULL REFERENCES cerner.encounter(encntr_id),

    -- Location at that time (coded)
    loc_facility_cd        BIGINT,
    loc_building_cd        BIGINT,
    loc_nurse_unit_cd      BIGINT,
    loc_room_cd            BIGINT,
    loc_bed_cd             BIGINT,

    -- Effective interval (preferred for state reconstruction)
    beg_effective_dt_tm    TIMESTAMPTZ NOT NULL,
    end_effective_dt_tm    TIMESTAMPTZ,

    -- Transaction timestamp (some Cerner extracts use this as “event time”)
    transaction_dt_tm      TIMESTAMPTZ NOT NULL DEFAULT now(),

    active_ind             SMALLINT NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS ix_elh_encntr_beg
    ON cerner.encntr_loc_hist (encntr_id, beg_effective_dt_tm DESC);

CREATE INDEX IF NOT EXISTS ix_elh_loc_keys
    ON cerner.encntr_loc_hist (loc_facility_cd, loc_building_cd, loc_nurse_unit_cd, loc_room_cd, loc_bed_cd);

CREATE INDEX IF NOT EXISTS ix_elh_txn
    ON cerner.encntr_loc_hist (transaction_dt_tm DESC);

-- -----------------------------
-- ENCNTR_PRSNL_RELTN (Attending/Admitting/Discharge doc, etc.)
-- Mirrors inpatient SQL joins. (role code stored as encntr_prsnl_r_cd)
-- -----------------------------
CREATE TABLE IF NOT EXISTS cerner.encntr_prsnl_reltn (
    encntr_prsnl_reltn_id  BIGSERIAL PRIMARY KEY,
    encntr_id              BIGINT NOT NULL REFERENCES cerner.encounter(encntr_id),
    prsnl_person_id        BIGINT NOT NULL REFERENCES cerner.prsnl(person_id),

    encntr_prsnl_r_cd      BIGINT NOT NULL, -- e.g., ATTENDDOC/ADMITDOC/DISCHARGEDOC codes
    active_ind             SMALLINT NOT NULL DEFAULT 1,

    beg_effective_dt_tm    TIMESTAMPTZ,
    end_effective_dt_tm    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_epr_encntr_role_active
    ON cerner.encntr_prsnl_reltn (encntr_id, encntr_prsnl_r_cd, active_ind);

-- -----------------------------
-- PROBLEM (simplified)
-- query aggregates PROBLEM.annotated_display.
-- -----------------------------
CREATE TABLE IF NOT EXISTS cerner.problem (
    problem_id          BIGSERIAL PRIMARY KEY,
    person_id           BIGINT NOT NULL REFERENCES cerner.person(person_id),
    annotated_display   TEXT,
    active_ind          SMALLINT NOT NULL DEFAULT 1,
    onset_dt_tm         TIMESTAMPTZ,
    updated_dt_tm       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_problem_person_active
    ON cerner.problem (person_id, active_ind);

-- -----------------------------
-- (Optional) ORDERS / ORDER_CATALOG minimal skeleton
-- -----------------------------
CREATE TABLE IF NOT EXISTS cerner.order_catalog (
    catalog_cd         BIGINT NOT NULL,
    catalog_type_cd    BIGINT NOT NULL,
    primary_mnemonic   TEXT,
    description        TEXT,
    PRIMARY KEY (catalog_cd, catalog_type_cd)
);

CREATE TABLE IF NOT EXISTS cerner.orders (
    order_id           BIGINT PRIMARY KEY,
    encntr_id          BIGINT NOT NULL REFERENCES cerner.encounter(encntr_id),
    catalog_cd         BIGINT NOT NULL,
    catalog_type_cd    BIGINT NOT NULL,
    orig_order_dt_tm   TIMESTAMPTZ NOT NULL,
    hna_order_mnemonic TEXT,
    product_id         BIGINT DEFAULT 0,
    order_status_cd    BIGINT,
    active_ind         SMALLINT NOT NULL DEFAULT 1,
    CONSTRAINT fk_orders_catalog
        FOREIGN KEY (catalog_cd, catalog_type_cd)
        REFERENCES cerner.order_catalog (catalog_cd, catalog_type_cd)
);

CREATE INDEX IF NOT EXISTS ix_orders_encntr_time
    ON cerner.orders (encntr_id, orig_order_dt_tm DESC);

-- -----------------------------
-- Convenience view: current location "as-of now" per encounter
-- -----------------------------
CREATE OR REPLACE VIEW cerner.v_encounter_current_loc AS
SELECT e.encntr_id,
       e.person_id,
       e.inpatient_admit_dt_tm,
       e.disch_dt_tm,
       elh.loc_facility_cd,
       elh.loc_building_cd,
       elh.loc_nurse_unit_cd,
       elh.loc_room_cd,
       elh.loc_bed_cd,
       elh.transaction_dt_tm
FROM cerner.encounter e
LEFT JOIN LATERAL (
    SELECT *
    FROM cerner.encntr_loc_hist h
    WHERE h.encntr_id = e.encntr_id
      AND h.active_ind = 1
    ORDER BY h.transaction_dt_tm DESC, h.beg_effective_dt_tm DESC
    LIMIT 1
) elh ON TRUE;