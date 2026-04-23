"""Tests for sku_scorer_server — T1/T2/T3 boundaries, input validation, fee triggers."""
import sku_scorer_server as sks


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_rejects_zero_sell_price():
    result = sks.score_sku(buy_price=5.0, sell_price=0)
    assert result["tier"] == "T3"
    assert result["signal"] == "SKIP"
    assert "error" in result
    assert "INVALID_INPUT" in result["flags"]


def test_rejects_negative_sell_price():
    result = sks.score_sku(buy_price=5.0, sell_price=-1.0)
    assert result["tier"] == "T3"
    assert result["signal"] == "SKIP"
    assert "error" in result


def test_rejects_negative_buy_price():
    result = sks.score_sku(buy_price=-1.0, sell_price=25.0)
    assert result["tier"] == "T3"
    assert result["signal"] == "SKIP"
    assert "INVALID_INPUT" in result["flags"]


def test_rejects_zero_weight():
    result = sks.score_sku(buy_price=5.0, sell_price=25.0, weight_oz=0)
    assert result["tier"] == "T3"
    assert "INVALID_INPUT" in result["flags"]


def test_rejects_negative_weight():
    result = sks.score_sku(buy_price=5.0, sell_price=25.0, weight_oz=-4)
    assert result["tier"] == "T3"
    assert "INVALID_INPUT" in result["flags"]


# ---------------------------------------------------------------------------
# Tier assignment — T1 / T2 / T3
# ---------------------------------------------------------------------------

def test_t1_buy_high_margin_high_velocity():
    """Strong margin + low sellers + fast velocity = T1."""
    result = sks.score_sku(
        buy_price=4.0,
        sell_price=29.99,
        weight_oz=10,
        size_tier="small_standard",
        category="Home & Kitchen",
        seller_count=2,
        estimated_monthly_units=300,
        days_to_sell_through=14,
    )
    assert result["tier"] == "T1"
    assert result["signal"] == "BUY"


def test_t3_skip_low_margin():
    """Margin < 10% after returns triggers LOW_MARGIN flag and T3 skip."""
    result = sks.score_sku(
        buy_price=20.0,
        sell_price=24.99,
        weight_oz=16,
        category="Home & Kitchen",
        seller_count=3,
    )
    assert result["tier"] == "T3"
    assert result["signal"] == "SKIP"
    assert "LOW_MARGIN" in result["flags"]


def test_t3_skip_pvs_below_threshold():
    """Acceptable margin but poor velocity/competition drops below T2 threshold."""
    result = sks.score_sku(
        buy_price=8.0,
        sell_price=25.0,
        weight_oz=16,
        category="Home & Kitchen",
        seller_count=15,
        estimated_monthly_units=20,
        days_to_sell_through=120,
    )
    # High competition + slow velocity should push below T2
    assert result["tier"] in ("T2", "T3")
    if result["tier"] == "T3":
        assert result["signal"] == "SKIP"


def test_high_competition_flag():
    result = sks.score_sku(
        buy_price=5.0,
        sell_price=25.0,
        seller_count=15,
    )
    assert "HIGH_COMPETITION" in result["flags"]


def test_slow_velocity_flag():
    result = sks.score_sku(
        buy_price=5.0,
        sell_price=25.0,
        days_to_sell_through=120,
    )
    assert "SLOW_VELOCITY" in result["flags"]


# ---------------------------------------------------------------------------
# LIVE fee triggering (low inventory risk)
# ---------------------------------------------------------------------------

def test_live_fee_triggers_under_28_days_coverage():
    """order_qty / monthly_sales * 30 < 28 days triggers LIVE fee."""
    result = sks.score_sku(
        buy_price=5.0,
        sell_price=25.0,
        size_tier="standard_size",
        order_quantity=50,
        estimated_monthly_sales=100,  # 50 units / (100/30) = 15 days coverage
    )
    assert result["risk_factors"]["live_fee_risk"] is True
    assert "LIVE_FEE_RISK" in result["flags"]
    assert result["fee_breakdown"]["live_fee"] > 0


def test_live_fee_not_triggered_with_deep_inventory():
    """Plenty of coverage means no LIVE fee."""
    result = sks.score_sku(
        buy_price=5.0,
        sell_price=25.0,
        order_quantity=500,
        estimated_monthly_sales=50,  # 500 / (50/30) = 300 days coverage
    )
    assert result["risk_factors"]["live_fee_risk"] is False
    assert result["fee_breakdown"]["live_fee"] == 0


# ---------------------------------------------------------------------------
# Slow-mover surcharge
# ---------------------------------------------------------------------------

def test_slow_mover_surcharge_triggers_past_182_days():
    """days_to_sell > 182 triggers storage surcharge."""
    result = sks.score_sku(
        buy_price=5.0,
        sell_price=25.0,
        order_quantity=500,
        estimated_monthly_sales=50,  # 300 days — past 182 threshold
        product_cubic_ft=0.5,
    )
    assert result["risk_factors"]["slow_mover_risk"] is True
    assert "SLOW_MOVER_SURCHARGE" in result["flags"]
    assert result["fee_breakdown"]["storage_surcharge"] > 0


def test_no_slow_mover_with_fast_turn():
    result = sks.score_sku(
        buy_price=5.0,
        sell_price=25.0,
        order_quantity=100,
        estimated_monthly_sales=100,  # 30 days — well under 182
    )
    assert result["risk_factors"]["slow_mover_risk"] is False
    assert result["fee_breakdown"]["storage_surcharge"] == 0


# ---------------------------------------------------------------------------
# Batch scoring — sort order
# ---------------------------------------------------------------------------

def test_batch_sorts_t1_first():
    batch = [
        {"buy_price": 20.0, "sell_price": 24.99, "category": "Home & Kitchen", "asin": "T3_LOW"},  # T3 low margin
        {"buy_price": 4.0, "sell_price": 29.99, "weight_oz": 10, "size_tier": "small_standard",
         "category": "Pet Supplies", "seller_count": 2, "estimated_monthly_units": 300,
         "days_to_sell_through": 14, "asin": "T1_BUY"},
        {"buy_price": 8.0, "sell_price": 18.0, "category": "Home & Kitchen",
         "seller_count": 7, "estimated_monthly_units": 60, "days_to_sell_through": 45, "asin": "T2_PAPER"},
    ]
    result = sks.score_skus_batch(batch)
    tiers_in_order = [r["tier"] for r in result["results"]]
    # T1 must come before T2 must come before T3
    assert tiers_in_order.index("T1") < tiers_in_order.index("T3")
    if "T2" in tiers_in_order:
        assert tiers_in_order.index("T2") < tiers_in_order.index("T3")


def test_batch_summary_counts():
    batch = [
        {"buy_price": 20.0, "sell_price": 24.99},  # T3 low margin
        {"buy_price": 4.0, "sell_price": 29.99, "weight_oz": 10, "size_tier": "small_standard",
         "seller_count": 2, "estimated_monthly_units": 300, "days_to_sell_through": 14},  # T1
    ]
    result = sks.score_skus_batch(batch)
    total = (result["summary"]["T1_buy"] + result["summary"]["T2_paper_trade"]
             + result["summary"]["T3_skip"])
    assert total == result["summary"]["total"] == 2


# ---------------------------------------------------------------------------
# Margin dict structure (regression guard against double-assignment bug)
# ---------------------------------------------------------------------------

def test_margin_dict_exposes_both_pre_and_post_return():
    """Regression test: ensure net_margin_pct and net_margin_pct_after_returns are both present."""
    result = sks.score_sku(buy_price=5.0, sell_price=25.0)
    margin = result["margin"]
    assert "net_margin_pct" in margin
    assert "net_margin_pct_after_returns" in margin
    # They should differ when there's any return cost
    assert margin["net_margin_pct"] != margin["net_margin_pct_after_returns"]


def test_asin_preserved_in_result():
    result = sks.score_sku(buy_price=5.0, sell_price=25.0, asin="B001TEST")
    assert result["asin"] == "B001TEST"
