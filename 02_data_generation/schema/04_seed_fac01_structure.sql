/* ============================================================================
   FAC_01 – Synthetic equivalent of the real hospital
   Structure only (no PHI, no real identifiers)
   ============================================================================ */

-- --------------------------------------------------------------------------
-- FACILITY
-- --------------------------------------------------------------------------

INSERT INTO cerner_ref.facility (facility_cd, facility_key, facility_type)
VALUES
  (900000001, 'FAC_01', 'CARDIAC_CENTER')
ON CONFLICT DO NOTHING;

-- --------------------------------------------------------------------------
-- BUILDINGS
-- --------------------------------------------------------------------------

INSERT INTO cerner_ref.building (building_cd, facility_cd, building_type)
VALUES
  (910000001, 900000001, 'OPD'),
  (910000002, 900000001, 'IPD')
ON CONFLICT DO NOTHING;

-- --------------------------------------------------------------------------
-- NURSE UNITS (FAC_01 – IPD only, capacities match your SQL exactly)
-- --------------------------------------------------------------------------

INSERT INTO cerner_ref.nurse_unit
(nurse_unit_cd, building_cd, unit_key, unit_display, unit_function, population_group, floor_flag)
VALUES
  (920000001, 910000002, 'IPD_ICU_SURG_GF',     'IPD ICU Surgery GF',         'ICU_AFTER_SURGERY', 'Adult',     'GF'),
  (920000002, 910000002, 'IPD_CCU_A_3F',        'IPD CCU A 3F',               'CCU',               'Adult',     '3F'),
  (920000003, 910000002, 'IPD_CCU_B_3F',        'IPD CCU B 3F',               'CCU',               'Adult',     '3F'),
  (920000004, 910000002, 'IPD_PICU_MED_2F',     'IPD Pediatric ICU 2F',       'ICU',               'Pediatric', '2F'),
  (920000005, 910000002, 'IPD_PICU_SURG_GF',    'IPD Pediatric ICU Surg GF',  'ICU_AFTER_SURGERY', 'Pediatric', 'GF'),
  (920000006, 910000002, 'IPD_WARD_SURG_1F',    'IPD Adult Surgery Ward 1F',  'AFTER_SURGERY',     'Adult',     '1F'),
  (920000007, 910000002, 'IPD_WARD_CARD_3F',    'IPD Adult Cardiology 3F',    'WARD',              'Adult',     '3F'),
  (920000008, 910000002, 'IPD_WARD_PED_2F',     'IPD Pediatric Ward 2F',      'WARD',              'Pediatric', '2F'),
  (920000009, 910000002, 'IPD_WARD_PEDSURG_1F', 'IPD Pediatric Surg Ward 1F', 'AFTER_SURGERY',     'Pediatric', '1F'),
  (920000010, 910000002, 'IPD_WARD_ADULT_2F',   'IPD Adult Ward 2F',          'WARD',              'Adult',     '2F'),
  (920000011, 910000002, 'IPD_CCU_CONG_2F',     'IPD Congenital CCU 2F',      'CCU',               'Adult',     '2F')
ON CONFLICT DO NOTHING;

-- --------------------------------------------------------------------------
-- UNIT CAPACITY (TOTAL = 186 beds)
-- --------------------------------------------------------------------------

INSERT INTO cerner_ref.unit_capacity (nurse_unit_cd, cap_beds)
VALUES
  (920000001, 15),
  (920000002, 18),
  (920000003, 7),
  (920000004, 12),
  (920000005, 14),
  (920000006, 25),
  (920000007, 25),
  (920000008, 14),
  (920000009, 30),
  (920000010, 20),
  (920000011, 6)
ON CONFLICT DO NOTHING;

-- --------------------------------------------------------------------------
-- ROOMS + BEDS
-- One bed per room (simplifies, capacity still correct)
-- Beds allocated strictly from unit_capacity
-- --------------------------------------------------------------------------

DO $$
DECLARE
    r RECORD;
    bed_counter BIGINT := 940000000;
    room_counter BIGINT := 930000000;
BEGIN
    FOR r IN
        SELECT nurse_unit_cd, cap_beds
        FROM cerner_ref.unit_capacity
    LOOP
        FOR i IN 1..r.cap_beds LOOP
            room_counter := room_counter + 1;
            bed_counter  := bed_counter  + 1;

            INSERT INTO cerner_ref.room (room_cd, nurse_unit_cd, room_type)
            VALUES (room_counter, r.nurse_unit_cd, 'IPD');

            INSERT INTO cerner_ref.bed (bed_cd, room_cd)
            VALUES (bed_counter, room_counter);
        END LOOP;
    END LOOP;
END $$;
