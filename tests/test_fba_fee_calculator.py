"""Tests for fba_fee_calculator_server — weight tier boundaries, referrals, prep, total."""
import fba_fee_calculator_server as fc


# ---------------------------------------------------------------------------
# Weight-tier boundaries for get_fba_fee
# ---------------------------------------------------------------------------

def test_small_standard_4oz_boundary():
    # Exactly 4oz is small_standard_4oz
    assert fc.get_fba_fee(weight_oz=4.0)["fba_fee"] == 3.06
    # Just over 4oz crosses into small_standard_8oz
    assert fc.get_fba_fee(weight_oz=4.01)["fba_fee"] == 3.15


def test_small_standard_16oz_boundary():
    assert fc.get_fba_fee(weight_oz=16.0)["fba_fee"] == 3.33
    # 16.01 crosses into large_standard_2lb
    assert fc.get_fba_fee(weight_oz=16.01)["fba_fee"] == 3.56


def test_large_standard_2lb_boundary():
    # 32oz = 2lb — top of 2lb tier
    assert fc.get_fba_fee(weight_oz=32.0)["fba_fee"] == 3.56
    # 32.01 crosses into 3lb
    assert fc.get_fba_fee(weight_oz=32.01)["fba_fee"] == 4.28


def test_large_standard_7lb_cap():
    # 7lb tier — any weight above 96oz (6lb) lands in 7lb
    assert fc.get_fba_fee(weight_oz=97)["fba_fee"] == 6.60
    assert fc.get_fba_fee(weight_oz=112)["fba_fee"] == 6.60  # still large_standard


def test_large_bulky_base():
    """large_bulky at or below 2lb uses base fee only."""
    result = fc.get_fba_fee(weight_oz=16.0, size_tier="large_bulky")
    assert result["fba_fee"] == 9.61


def test_large_bulky_per_pound_math():
    """large_bulky over 2lb adds per-pound surcharge."""
    # 5lb = 2lb base + 3 extra lb × $0.38
    result = fc.get_fba_fee(weight_oz=80.0, size_tier="large_bulky")
    expected = round(9.61 + 3 * 0.38, 2)
    assert result["fba_fee"] == expected


def test_invalid_weight_returns_error():
    result = fc.get_fba_fee(weight_oz=0)
    assert "error" in result
    assert result["fba_fee"] == 0.0


def test_invalid_negative_weight_returns_error():
    result = fc.get_fba_fee(weight_oz=-5)
    assert "error" in result


# ---------------------------------------------------------------------------
# Referral fee
# ---------------------------------------------------------------------------

def test_referral_fee_electronics():
    result = fc.calculate_referral_fee("Electronics", 100.0)
    assert result["referral_fee"] == 8.0  # 8%
    assert result["rate"] == "8%"


def test_referral_fee_jewelry():
    result = fc.calculate_referral_fee("Jewelry", 100.0)
    assert result["referral_fee"] == 20.0  # 20%


def test_referral_fee_defaults_to_15_percent():
    result = fc.calculate_referral_fee("Some Category We Haven't Mapped", 100.0)
    assert result["referral_fee"] == 15.0


def test_referral_fee_rejects_zero_price():
    result = fc.calculate_referral_fee("Electronics", 0)
    assert "error" in result


# ---------------------------------------------------------------------------
# Prep cost
# ---------------------------------------------------------------------------

def test_prep_cost_standard_no_addons():
    result = fc.calculate_prep_cost(weight_lbs=1.0, size_tier="standard")
    # base (1.75) + label (0.20) + inbound (0.45 × 1.0) = 2.40
    assert result["total_prep_cost"] == 2.40


def test_prep_cost_oversize_with_bag_and_bubble():
    result = fc.calculate_prep_cost(
        weight_lbs=2.0, size_tier="oversize",
        needs_poly_bag=True, needs_bubble_wrap=True,
    )
    # base (3.50) + poly (0.50) + bubble (0.75) + label (0.20) + inbound (0.45 × 2) = 5.85
    assert result["total_prep_cost"] == 5.85


def test_prep_cost_scales_with_weight():
    light = fc.calculate_prep_cost(weight_lbs=1.0)["total_prep_cost"]
    heavy = fc.calculate_prep_cost(weight_lbs=5.0)["total_prep_cost"]
    assert heavy > light


# ---------------------------------------------------------------------------
# Total fees — integrated stack
# ---------------------------------------------------------------------------

def test_total_fees_breakdown_sums_correctly():
    result = fc.calculate_total_fees(
        sale_price=30.0,
        weight_oz=16,
        size_tier="standard_size",
        category="Home & Kitchen",
        weight_lbs=1.0,
    )
    breakdown = result["fee_breakdown"]
    total_from_breakdown = round(
        breakdown["fba_fulfillment"]
        + breakdown["referral_fee"]
        + breakdown["prep_cost"]
        + breakdown["inbound_placement_fee"],
        2,
    )
    assert result["total_fees"] == total_from_breakdown


def test_total_fees_revenue_after_fees():
    result = fc.calculate_total_fees(sale_price=30.0)
    assert result["revenue_after_fees"] == round(30.0 - result["total_fees"], 2)


def test_total_fees_large_bulky_uses_oversize_prep():
    """large_bulky size_tier should trigger oversize prep cost ($3.50 base vs $1.75)."""
    standard = fc.calculate_total_fees(sale_price=50, size_tier="standard_size")
    bulky = fc.calculate_total_fees(sale_price=50, size_tier="large_bulky")
    # Bulky prep alone is ~$1.75 more; placement is also $2.41 vs $0.25
    assert bulky["fee_breakdown"]["prep_cost"] > standard["fee_breakdown"]["prep_cost"]
    assert bulky["fee_breakdown"]["inbound_placement_fee"] > standard["fee_breakdown"]["inbound_placement_fee"]


def test_total_fees_pct_formatted():
    result = fc.calculate_total_fees(sale_price=30.0)
    assert result["fees_as_pct_of_sale"].endswith("%")
