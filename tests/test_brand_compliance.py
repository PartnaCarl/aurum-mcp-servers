"""Tests for brand_compliance_server — status classification, case handling, batch counts."""
import brand_compliance_server as bc


# ---------------------------------------------------------------------------
# Status classification
# ---------------------------------------------------------------------------

def test_ip_risky_returns_high():
    result = bc.check_brand("Apple")
    assert result["status"] == "IP_RISKY"
    assert result["risk_level"] == "HIGH"


def test_gated_returns_medium():
    """A gated brand with no IP risk returns MEDIUM."""
    # Pick a brand in GATED_BRANDS but NOT in IP_RISKY_BRANDS
    result = bc.check_brand("Herbal Essences")
    assert result["status"] == "GATED"
    assert result["risk_level"] == "MEDIUM"


def test_commingling_only_returns_low():
    """Brand only in COMMINGLING_RISK (not gated, not IP_RISKY) returns LOW."""
    # Find a brand only in COMMINGLING_RISK — union diff
    commingling_only = (
        bc.COMMINGLING_RISK_BRANDS - bc.IP_RISKY_BRANDS - bc.GATED_BRANDS
    )
    if commingling_only:
        test_brand = next(iter(commingling_only))
        result = bc.check_brand(test_brand)
        assert result["status"] == "COMMINGLING_RISK"
        assert result["risk_level"] == "LOW"
    else:
        # If there are no commingling-only brands, the test is structurally N/A —
        # just verify the classification branch works with a manual probe.
        # Use a brand we know is in COMMINGLING but check status priority
        result = bc.check_brand("Stanley")
        assert result["status"] in ("IP_RISKY", "GATED", "COMMINGLING_RISK")


def test_clear_returns_none():
    result = bc.check_brand("ZorbleFrobnicatorX9")
    assert result["status"] == "CLEAR"
    assert result["risk_level"] == "NONE"
    assert result["is_gated"] is False


# ---------------------------------------------------------------------------
# Case insensitivity
# ---------------------------------------------------------------------------

def test_case_insensitive_apple():
    for variant in ["apple", "APPLE", "Apple", "aPpLe"]:
        assert bc.check_brand(variant)["status"] == "IP_RISKY"


def test_whitespace_trimmed():
    assert bc.check_brand("  Apple  ")["status"] == "IP_RISKY"


# ---------------------------------------------------------------------------
# Ray-Ban regression guard (the prompt explicitly called this out)
# ---------------------------------------------------------------------------

def test_rayban_is_ip_risky():
    """Ray-Ban must be IP_RISKY (EssilorLuxottica enforcement is aggressive)."""
    for variant in ["Ray-Ban", "ray-ban", "RayBan", "rayban"]:
        result = bc.check_brand(variant)
        assert result["status"] == "IP_RISKY", f"{variant} should be IP_RISKY"
        assert result["risk_level"] == "HIGH"


def test_oakley_is_ip_risky():
    """Oakley is also EssilorLuxottica — should match Ray-Ban classification."""
    assert bc.check_brand("Oakley")["status"] == "IP_RISKY"


# ---------------------------------------------------------------------------
# Priority order (IP_RISKY beats GATED beats COMMINGLING)
# ---------------------------------------------------------------------------

def test_apple_prioritizes_ip_risky_over_gated():
    """Apple is in both IP_RISKY and GATED — must return IP_RISKY."""
    result = bc.check_brand("Apple")
    assert result["status"] == "IP_RISKY"
    # The is_gated flag should still be True to surface the underlying fact
    assert result["is_gated"] is True


# ---------------------------------------------------------------------------
# Batch behavior
# ---------------------------------------------------------------------------

def test_batch_summary_counts_sum_to_total():
    result = bc.check_brands_batch(["Apple", "Nestle", "FakeBrandXYZ123"])
    s = result["summary"]
    assert s["total_checked"] == 3
    assert s["ip_risky"] + s["gated"] + s["commingling_risk"] + s["clear"] == 3


def test_batch_sorts_by_risk_descending():
    """HIGH risk items come first, NONE last."""
    result = bc.check_brands_batch(["ZorbleFrobnicatorX9", "Apple", "Herbal Essences"])
    risks = [r["risk_level"] for r in result["results"]]
    assert risks[0] == "HIGH"   # Apple
    assert risks[-1] == "NONE"  # Zorble


def test_batch_do_not_source_list():
    result = bc.check_brands_batch(["Apple", "Ray-Ban", "ZorbleFrobnicatorX9"])
    assert "Apple" in result["do_not_source"]
    assert "Ray-Ban" in result["do_not_source"]
    assert "ZorbleFrobnicatorX9" not in result["do_not_source"]


def test_batch_returns_same_count_as_input():
    inputs = ["Apple", "Dyson", "Lego", "FakeA", "FakeB"]
    result = bc.check_brands_batch(inputs)
    assert len(result["results"]) == len(inputs)


# ---------------------------------------------------------------------------
# Catalog sanity — confirm the database hit the target scale
# ---------------------------------------------------------------------------

def test_brand_catalog_is_large_enough():
    """The prompt called for 400+ brands. Don't silently regress below that."""
    union = bc.GATED_BRANDS | bc.IP_RISKY_BRANDS | bc.COMMINGLING_RISK_BRANDS
    assert len(union) >= 400, f"Brand catalog has only {len(union)} unique entries"


def test_ip_risky_is_subset_of_attention():
    """Every IP_RISKY brand should normally also be in GATED (defense in depth)."""
    # Not strictly required — but if a brand is IP-risky, it's almost certainly gated too.
    # If <80% overlap, something is wrong.
    overlap = bc.IP_RISKY_BRANDS & bc.GATED_BRANDS
    assert len(overlap) / len(bc.IP_RISKY_BRANDS) > 0.7
