from src.prediction.taxonomy import canonical_categories, canonical_label


def test_category_case_and_spacing_do_not_fragment_learning():
    assert canonical_label("geopolitics") == "GEOPOLITICS"
    assert canonical_label("Geopolitics") == "GEOPOLITICS"
    assert canonical_label("energy risk") == "ENERGY_RISK"
    assert canonical_label("energy-risk") == "ENERGY_RISK"


def test_category_list_deduplicates_after_canonicalization():
    assert canonical_categories(["oil", "OIL", "Oil "]) == ["OIL"]
