-- 02_data_generation/schema/01_cerner_core.sql
-- Cerner-shaped core reference objects for a local PostgreSQL experiment.
-- Focus: CODE_VALUE, PERSON, PRSNL, and alias tables used widely in Millennium-style SQL.

CREATE SCHEMA IF NOT EXISTS cerner;

-- -----------------------------
-- CODE_VALUE (Cerner-style codeset table)
-- -----------------------------
CREATE TABLE IF NOT EXISTS cerner.code_value (
    code_value           BIGINT PRIMARY KEY,
    code_set             BIGINT NOT NULL,
    cdf_meaning          TEXT,
    display              TEXT NOT NULL,
    description          TEXT,
    active_ind           SMALLINT NOT NULL DEFAULT 1,
    beg_effective_dt_tm  TIMESTAMPTZ,
    end_effective_dt_tm  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_code_value_codeset_display
    ON cerner.code_value (code_set, display);

CREATE INDEX IF NOT EXISTS ix_code_value_codeset_meaning
    ON cerner.code_value (code_set, cdf_meaning);

-- -----------------------------
-- PERSON (patient/person master)
-- -----------------------------
CREATE TABLE IF NOT EXISTS cerner.person (
    person_id            BIGINT PRIMARY KEY,
    name_full_formatted  TEXT,
    birth_dt_tm          TIMESTAMPTZ,
    deceased_dt_tm       TIMESTAMPTZ,
    sex_cd               BIGINT,
    nationality_cd       BIGINT,
    active_ind           SMALLINT NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS ix_person_sex ON cerner.person (sex_cd);
CREATE INDEX IF NOT EXISTS ix_person_nationality ON cerner.person (nationality_cd);

-- -----------------------------
-- PRSNL (personnel/provider master)
-- -----------------------------
CREATE TABLE IF NOT EXISTS cerner.prsnl (
    person_id            BIGINT PRIMARY KEY,
    name_full_formatted  TEXT,
    active_ind           SMALLINT NOT NULL DEFAULT 1
);

-- -----------------------------
-- PERSON_ALIAS (MRN, etc.)
-- -----------------------------
CREATE TABLE IF NOT EXISTS cerner.person_alias (
    person_alias_id        BIGSERIAL PRIMARY KEY,
    person_id              BIGINT NOT NULL REFERENCES cerner.person(person_id),
    person_alias_type_cd   BIGINT NOT NULL,
    alias                  TEXT NOT NULL,
    active_ind             SMALLINT NOT NULL DEFAULT 1,
    beg_effective_dt_tm    TIMESTAMPTZ,
    end_effective_dt_tm    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_person_alias_person_type_active
    ON cerner.person_alias (person_id, person_alias_type_cd, active_ind);

-- -----------------------------
-- ENCNTR_ALIAS (FIN NBR, etc.)
-- -----------------------------
CREATE TABLE IF NOT EXISTS cerner.encntr_alias (
    encntr_alias_id        BIGSERIAL PRIMARY KEY,
    encntr_id              BIGINT NOT NULL,
    encntr_alias_type_cd   BIGINT NOT NULL,
    alias                  TEXT NOT NULL,
    active_ind             SMALLINT NOT NULL DEFAULT 1,
    beg_effective_dt_tm    TIMESTAMPTZ,
    end_effective_dt_tm    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_encntr_alias_encntr_type_active
    ON cerner.encntr_alias (encntr_id, encntr_alias_type_cd, active_ind);
