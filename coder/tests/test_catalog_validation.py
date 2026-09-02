import pytest
from coder.catalog import load_catalog


def test_gdl_027_flagged_as_inconsistent():
    catalog = load_catalog()
    guideline = catalog.get_guideline("GDL-027")
    assert guideline is not None, "GDL-027 should exist"
    assert guideline.flagged_inconsistent, "GDL-027 should be flagged as inconsistent"
    assert "AB30" in guideline.linked_codes
    assert "Ménière" in guideline.inconsistency_reason or "topical keyword overlap" in guideline.inconsistency_reason


def test_all_guideline_codes_exist_in_catalog():
    catalog = load_catalog()
    for guideline in catalog.get_all_guidelines():
        for code in guideline.linked_codes:
            assert code in catalog.codes, f"Guideline {guideline.id} references non-existent code {code}"


def test_catalog_loads_all_codes():
    catalog = load_catalog()
    assert len(catalog.codes) == 288


def test_catalog_loads_all_guidelines():
    catalog = load_catalog()
    assert len(catalog.guidelines) == 31