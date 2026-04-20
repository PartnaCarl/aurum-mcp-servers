"""
sku_scorer_server.py — AURUM FBA SKU Scorer MCP Server

Score any product using the T1/T2/T3 decision engine. Input a buy price and
product details, get a BUY / PAPER TRADE / SKIP decision with full margin breakdown.

Includes 2026 FBA fees, AMSCO prep costs, inbound placement fees, return rate
modeling, LIVE fee risk, and slow-mover surcharge — the complete cost stack.

Tools:
  - score_sku: Score a single product
  - score_skus_batch: Score multiple products at once
"""

from fastmcp import FastMCP
from typing import List, Optional

mcp = FastMCP("FBA SKU Scorer")

# ---------------------------------------------------------------------------
# Constants — 2026 fee tables and scoring parameters
# ---------------------------------------------------------------------------

MARGIN_BUFFER_PCT = 0.15  # Buffered margin must clear this before tier assignment

FBA_FEES_2026 = {
    "small_standard_4oz":  3.06,
    "small_standard_8oz":  3.15,
    "small_standard_12oz": 3.24,
    "small_standard_16oz": 3.33,
    "large_standard_2lb":  3.56,
    "large_standard_3lb":  4.28,
    "large_standard_4lb":  5.09,
    "large_standard_5lb":  5.48,
    "large_standard_6lb":  6.32,
    "large_standard_7lb":  6.60,
    "large_bulky_base":    9.61,
    "large_bulky_per_lb":  0.38,
}

INBOUND_PLACEMENT_FEES = {
    "small_standard": 0.20,
    "standard_size":  0.25,
    "large_bulky":    2.41,
}

CATEGORY_RETURN_RATES = {
    "Electronics":             0.15,
    "Apparel":                 0.25,
    "Grocery & Gourmet Food":  0.03,
    "Health & Household":      0.08,
    "Health & Beauty":         0.08,
    "Beauty & Personal Care":  0.08,
    "Home & Kitchen":          0.10,
    "Toys & Games":            0.12,
    "Sports & Outdoors":       0.07,
    "Pet Supplies":            0.06,
    "Baby & Toddler":          0.09,
    "Office Products":         0.05,
    "Patio & Garden":          0.08,
    "Tools & Home Improvement":0.09,
}
DEFAULT_RETURN_RATE = 0.08

REFERRAL_RATES = {
    "Electronics": 0.08, "Computers": 0.08,
    "Grocery & Gourmet Food": 0.08,
    "Clothing": 0.17, "Apparel": 0.17,
    "Jewelry": 0.20, "Watches": 0.16,
    "Automotive": 0.12,
}
DEFAULT_REFERRAL_RATE = 0.15

LIVE_FEE_BY_SIZE = {
    "standard_size":  0.32,
    "small_standard": 0.32,
    "large_bulky":    0.47,
}
LIVE_FEE_DAYS_THRESHOLD = 28
SLOW_MOVER_DAYS_THRESHOLD = 182
STORAGE_SURCHARGE_PER_CUBIC_FT = 1.50
DEFAULT_CUBIC_FT = 0.25

PREP_BASE = {"standard": 1.75, "oversize": 3.50}
PREP_LABEL = 0.20
PREP_INBOUND_PER_LB = 0.45


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_fba_fee(weight_oz: float, size_tier: str) -> float:
    if size_tier == "large_bulky":
        weight_lb = weight_oz / 16
        return FBA_FEES_2026["large_bulky_base"] + max(0, weight_lb - 2) * FBA_FEES_2026["large_bulky_per_lb"]
    if weight_oz <= 4:   return FBA_FEES_2026["small_standard_4oz"]
    if weight_oz <= 8:   return FBA_FEES_2026["small_standard_8oz"]
    if weight_oz <= 12:  return FBA_FEES_2026["small_standard_12oz"]
    if weight_oz <= 16:  return FBA_FEES_2026["small_standard_16oz"]
    if weight_oz <= 32:  return FBA_FEES_2026["large_standard_2lb"]
    if weight_oz <= 48:  return FBA_FEES_2026["large_standard_3lb"]
    if weight_oz <= 64:  return FBA_FEES_2026["large_standard_4lb"]
    if weight_oz <= 80:  return FBA_FEES_2026["large_standard_5lb"]
    if weight_oz <= 96:  return FBA_FEES_2026["large_standard_6lb"]
    return FBA_FEES_2026["large_standard_7lb"]


def _seller_weight(seller_count: int) -> float:
    if seller_count <= 3:  return 1.00
    if seller_count <= 6:  return 0.75
    if seller_count <= 10: return 0.50
    return 0.15


def _score_one(
    buy_price: float,
    sell_price: float,
    weight_oz: float,
    size_tier: str,
    category: str,
    seller_count: int,
    estimated_monthly_units: int,
    days_to_sell_through: int,
    weight_lbs: float,
    order_quantity: int,
    estimated_monthly_sales: int,
    product_cubic_ft: float,
) -> dict:
    # FBA fee
    fba_fee = _get_fba_fee(weight_oz, size_tier)

    # Referral fee
    referral_fee = sell_price * REFERRAL_RATES.get(category, DEFAULT_REFERRAL_RATE)

    # Prep cost (AMSCO)
    prep_tier = "oversize" if size_tier == "large_bulky" else "standard"
    prep_cost = PREP_BASE[prep_tier] + PREP_LABEL + (PREP_INBOUND_PER_LB * weight_lbs)

    # Inbound placement fee
    placement_fee = INBOUND_PLACEMENT_FEES.get(size_tier, INBOUND_PLACEMENT_FEES["standard_size"])

    # LIVE fee (low inventory risk)
    if estimated_monthly_sales > 0 and order_quantity > 0:
        days_covered = order_quantity / (estimated_monthly_sales / 30)
    else:
        days_covered = 999
    live_fee_risk = days_covered < LIVE_FEE_DAYS_THRESHOLD
    live_fee = LIVE_FEE_BY_SIZE.get(size_tier, 0.32) if live_fee_risk else 0.0

    # Slow-mover surcharge
    if estimated_monthly_sales > 0 and order_quantity > 0:
        days_to_sell = order_quantity / (estimated_monthly_sales / 30)
    else:
        days_to_sell = float(days_to_sell_through)
    slow_mover_risk = days_to_sell > SLOW_MOVER_DAYS_THRESHOLD
    if slow_mover_risk:
        months_over = (days_to_sell - 182) / 30
        cubic = product_cubic_ft if product_cubic_ft > 0 else DEFAULT_CUBIC_FT
        storage_surcharge = cubic * STORAGE_SURCHARGE_PER_CUBIC_FT * months_over
    else:
        storage_surcharge = 0.0

    # Net margin
    total_costs = buy_price + fba_fee + prep_cost + placement_fee + referral_fee + live_fee + storage_surcharge
    net_margin = sell_price - total_costs
    net_margin_pct = net_margin / sell_price if sell_price > 0 else 0.0

    # Return rate adjustment
    return_rate = CATEGORY_RETURN_RATES.get(category, DEFAULT_RETURN_RATE)
    return_cost = buy_price * return_rate * 0.5
    margin_after_returns = net_margin - return_cost
    net_margin_pct = margin_after_returns / sell_price if sell_price > 0 else 0.0

    # Buffered margin
    buffered_margin_pct = net_margin_pct * (1 - MARGIN_BUFFER_PCT)

    # Seller weight and scoring
    sw = _seller_weight(seller_count)
    units_per_seller = estimated_monthly_units / max(seller_count, 1)
    sell_through_factor = 1.0 / max(days_to_sell_through, 1)
    pvs_score = units_per_seller * buffered_margin_pct * sell_through_factor * sw

    # Flags
    flags = []
    if net_margin_pct < 0.10:   flags.append("LOW_MARGIN")
    if seller_count > 10:        flags.append("HIGH_COMPETITION")
    if days_to_sell_through > 90: flags.append("SLOW_VELOCITY")
    if slow_mover_risk:          flags.append("SLOW_MOVER_SURCHARGE")
    if live_fee_risk:            flags.append("LIVE_FEE_RISK")

    # Tier assignment
    if "LOW_MARGIN" in flags:
        tier, signal = "T3", "SKIP"
        recommendation = f"Net margin {net_margin_pct:.1%} is below 10% minimum. Do not source."
    elif pvs_score >= 0.8:
        tier, signal = "T1", "BUY"
        recommendation = f"Strong margin ({net_margin_pct:.1%}) and velocity. Source this product."
        if flags: recommendation += f" Flags: {', '.join(flags)}."
    elif pvs_score >= 0.4:
        tier, signal = "T2", "PAPER TRADE"
        recommendation = "Moderate score. Track 30 days before committing capital."
        if flags: recommendation += f" Flags: {', '.join(flags)}."
    else:
        tier, signal = "T3", "SKIP"
        recommendation = f"PVS score {pvs_score:.4f} below T2 threshold (0.40). Pass."
        if flags: recommendation += f" Flags: {', '.join(flags)}."

    return {
        "tier": tier,
        "signal": signal,
        "pvs_score": round(pvs_score, 6),
        "recommendation": recommendation,
        "margin": {
            "buy_price": round(buy_price, 2),
            "sell_price": round(sell_price, 2),
            "net_margin_dollars": round(net_margin, 2),
            "net_margin_pct": f"{net_margin_pct:.1%}",
            "buffered_margin_pct": f"{buffered_margin_pct:.1%}",
            "margin_after_returns": round(margin_after_returns, 2),
        },
        "fee_breakdown": {
            "fba_fulfillment": round(fba_fee, 2),
            "referral_fee": round(referral_fee, 2),
            "prep_cost_amsco": round(prep_cost, 2),
            "inbound_placement_fee": round(placement_fee, 2),
            "live_fee": round(live_fee, 2),
            "storage_surcharge": round(storage_surcharge, 2),
            "total_fees": round(fba_fee + prep_cost + placement_fee + referral_fee + live_fee + storage_surcharge, 2),
        },
        "risk_factors": {
            "return_rate": f"{return_rate:.0%}",
            "return_cost_per_unit": round(return_cost, 2),
            "live_fee_risk": live_fee_risk,
            "slow_mover_risk": slow_mover_risk,
        },
        "flags": flags,
        "scoring_inputs": {
            "seller_count": seller_count,
            "seller_weight": sw,
            "units_per_seller_per_month": round(units_per_seller, 2),
            "sell_through_days": days_to_sell_through,
        },
    }


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def score_sku(
    buy_price: float,
    sell_price: float,
    weight_oz: float = 16.0,
    size_tier: str = "standard_size",
    category: str = "Home & Kitchen",
    seller_count: int = 5,
    estimated_monthly_units: int = 50,
    days_to_sell_through: int = 30,
    weight_lbs: float = 1.0,
    order_quantity: int = 0,
    estimated_monthly_sales: int = 0,
    product_cubic_ft: float = 0.25,
    asin: Optional[str] = None,
) -> dict:
    """
    Score a product using the AURUM T1/T2/T3 FBA decision engine.

    Returns a BUY / PAPER TRADE / SKIP decision with full margin breakdown
    including all 2026 fees, AMSCO prep costs, and return rate adjustments.

    Tier thresholds:
      T1 (BUY)         — PVS score >= 0.8
      T2 (PAPER TRADE) — PVS score >= 0.4
      T3 (SKIP)        — PVS score < 0.4 or margin < 10%

    Args:
        buy_price: Your wholesale cost per unit.
        sell_price: Current Amazon sale price.
        weight_oz: Product weight in ounces (default 16oz).
        size_tier: 'small_standard', 'standard_size', or 'large_bulky'.
        category: Amazon product category.
        seller_count: Number of FBA sellers on the listing.
        estimated_monthly_units: Estimated total monthly units sold by all sellers.
        days_to_sell_through: How many days to sell your inventory.
        weight_lbs: Unit weight in lbs (for prep/inbound cost).
        order_quantity: Units you plan to order (for LIVE fee calculation).
        estimated_monthly_sales: Your estimated monthly sales velocity.
        product_cubic_ft: Product volume in cubic feet (default 0.25).
        asin: Optional ASIN for reference.

    Returns:
        dict with tier, signal, pvs_score, recommendation, margin, fee_breakdown, and flags.
    """
    result = _score_one(
        buy_price=buy_price,
        sell_price=sell_price,
        weight_oz=weight_oz,
        size_tier=size_tier,
        category=category,
        seller_count=seller_count,
        estimated_monthly_units=estimated_monthly_units,
        days_to_sell_through=days_to_sell_through,
        weight_lbs=weight_lbs,
        order_quantity=order_quantity,
        estimated_monthly_sales=estimated_monthly_sales,
        product_cubic_ft=product_cubic_ft,
    )
    if asin:
        result["asin"] = asin
    return result


@mcp.tool()
def score_skus_batch(skus: List[dict]) -> dict:
    """
    Score multiple products at once. Returns results sorted T1 first.

    Each item in the list should be a dict with the same fields as score_sku.
    Only buy_price and sell_price are required; all others use defaults.

    Example input:
      [
        {"asin": "B001TEST", "buy_price": 12.50, "sell_price": 28.99,
         "category": "Pet Supplies", "seller_count": 3, "weight_oz": 20},
        {"buy_price": 8.00, "sell_price": 15.99, "category": "Home & Kitchen"}
      ]

    Args:
        skus: List of product dicts to score.

    Returns:
        dict with summary (T1/T2/T3 counts) and scored results sorted by tier and PVS score.
    """
    results = []
    for sku in skus:
        result = _score_one(
            buy_price=float(sku.get("buy_price", 0)),
            sell_price=float(sku.get("sell_price", 0)),
            weight_oz=float(sku.get("weight_oz", 16.0)),
            size_tier=str(sku.get("size_tier", "standard_size")),
            category=str(sku.get("category", "Home & Kitchen")),
            seller_count=int(sku.get("seller_count", 5)),
            estimated_monthly_units=int(sku.get("estimated_monthly_units", 50)),
            days_to_sell_through=int(sku.get("days_to_sell_through", 30)),
            weight_lbs=float(sku.get("weight_lbs", 1.0)),
            order_quantity=int(sku.get("order_quantity", 0)),
            estimated_monthly_sales=int(sku.get("estimated_monthly_sales", 0)),
            product_cubic_ft=float(sku.get("product_cubic_ft", 0.25)),
        )
        if "asin" in sku:
            result["asin"] = sku["asin"]
        if "title" in sku:
            result["title"] = sku["title"]
        results.append(result)

    tier_order = {"T1": 0, "T2": 1, "T3": 2}
    results.sort(key=lambda r: (tier_order.get(r["tier"], 9), -r["pvs_score"]))

    return {
        "summary": {
            "total": len(results),
            "T1_buy": sum(1 for r in results if r["tier"] == "T1"),
            "T2_paper_trade": sum(1 for r in results if r["tier"] == "T2"),
            "T3_skip": sum(1 for r in results if r["tier"] == "T3"),
        },
        "results": results,
    }


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="http", host="0.0.0.0", port=port)
