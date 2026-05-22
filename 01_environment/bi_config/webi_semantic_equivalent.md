# Web Intelligence / BI Semantic Layer Equivalent

This document explains how the experiment maps to a BI semantic layer such as SAP BusinessObjects Web Intelligence.

## Conventional semantic layer

A semantic layer maps technical database fields into business-friendly concepts such as:

- Facility
- Building
- Nurse Unit
- Room
- Bed
- Census Count
- Discharge Count
- Occupancy Ratio

In a conventional BI setup, the semantic layer improves usability and governance, but query execution still occurs at runtime against underlying relational tables.

## Live SQL equivalent

The live SQL semantic equivalent exposes business objects over joins among:

- cerner.person
- cerner.encounter
- cerner.encntr_loc_hist
- cerner.orders
- cerner.order_catalog
- cerner_ref.facility
- cerner_ref.building
- cerner_ref.nurse_unit
- cerner_ref.room
- cerner_ref.bed
- cerner_ref.unit_capacity

## ACBP equivalent

The ACBP semantic equivalent exposes objects from precomputed relational artifacts:

- Boolean state surface
- Valid decision space
- Dashboard query views

## Key distinction

    Semantic layer: business abstraction over runtime evaluation
    ACBP: compiled state representation before dashboard execution

A semantic layer improves names and governance. ACBP changes execution by compiling operational validity into SQL-native structures.