"""
fba_fee_calculator_server.py — AURUM FBA Fee Calculator MCP Server

Tools:
  - get_fba_fee: 2026 FBA fulfillment fee by weight and size tier
  - calculate_referral_fee: Amazon referral fee by category
  - calculate_prep_cost: AMSCO prep cost estimate
  - calculate_total_fees: All-in fee breakdown for a product
"""

from fastmcp import FastMCP

mcp = FastMCP("FBA Fee Calculator 2026")

# ---------------------------------------------------------------------------
# 2026 FBA Fee Tables (effective 2026-01-15)
# ---------------------------------------------------------------------------

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

REFERRAL_RATES = {
    "Electronics":             0.08,
    "Computers":               0.08,
    "Camera & Photo":          0.08,
    "Toys & Games":            0.15,
    "Home & Kitchen":          0.15,
    "Health & Household":      0.15,
    "Health & Beauty":         0.15,
    "Beauty & Personal Care":  0.15,
    "Pet Supplies":            0.15,
    "Baby & Toddler":          0.15,
    "Sports & Outdoors":       0.15,
    "Office Products":         0.15,
    "Tools & Home Improvement":0.15,
    "Patio & Garden":          0.15,
    "Grocery & Gourmet Food":  0.08,
    "Clothing":                0.17,
    "Apparel":                 0.17,
    "Shoes":                   0.15,
    "Jewelry":                 0.20,
    "Watches":                 0.16,
    "Automotive":              0.12,
    "Books":                   0.15,
    "Music":                   0.15,
    "Video Games":             0.15,
}
DEFAULT_REFERRAL_RATE = 0.15

PREP_COST_CONFIG = {
    "standard_prep":         1.75,
    "oversize_prep":         3.50,
    "poly_bag":              0.50,
    "bubble_wrap":           0.75,
    "label_per_unit":        0.20,
    "inbound_shipping_per_lb": 0.45,
}


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_fba_fee(weight_oz: float = 16.0, size_tier: str = "standard_size") -> dict:
    """
    Calculate the 2026 Amazon FBA fulfillment fee for a product.

    Includes the April 2026 3.5% surcharge already baked into the fee tables.
    Effective date: 2026-01-15.

    Args:
        weight_oz: Product weight in ounces. Default 16oz (1 lb).
        size_tier: One of 'small_standard', 'standard_size', or 'large_bulky'.

    Returns:
        dict with fba_fee (dollars), size_tier, weight_oz, and effective_date.
    """
    if size_tier == "large_bulky":
        weight_lb = weight_oz / 16
        extra_lb = max(0, weight_lb - 2)
        fee = FBA_FEES_2026["large_bulky_base"] + extra_lb * FBA_FEES_2026["large_bulky_per_lb"]
    elif weight_oz <= 4:   fee = FBA_FEES_2026["small_standard_4oz"]
    elif weight_oz <= 8:   fee = FBA_FEES_2026["small_standard_8oz"]
    elif weight_oz <= 12:  fee = FBA_FEES_2026["small_standard_12oz"]
    elif weight_oz <= 16:  fee = FBA_FEES_2026["small_standard_16oz"]
    elif weight_oz <= 32:  fee = FBA_FEES_2026["large_standard_2lb"]
    elif weight_oz <= 48:  fee = FBA_FEES_2026["large_standard_3lb"]
    elif weight_oz <= 64:  fee = FBA_FEES_2026["large_standard_4lb"]
    elif weight_oz <= 80:  fee = FBA_FEES_2026["large_standard_5lb"]
    elif weight_oz <= 96:  fee = FBA_FEES_2026["large_standard_6lb"]
    else:                  fee = FBA_FEES_2026["large_standard_7lb"]

    return {
        "fba_fee": round(fee, 2),
        "size_tier": size_tier,
        "weight_oz": weight_oz,
        "effective_date": "2026-01-15",
        "note": "Includes April 2026 3.5% surcharge",
    }


@mcp.tool()
def calculate_referral_fee(category: str, sale_price: float) -> dict:
    """
    Calculate Amazon referral fee for a product.

    Args:
        category: Amazon product category (e.g. 'Pet Supplies', 'Home & Kitchen').
        sale_price: Amazon sale price in dollars.

    Returns:
        dict with referral_fee (dollars), rate (percent), and category used.
    """
    rate = REFERRAL_RATES.get(category, DEFAULT_REFERRAL_RATE)
    fee = round(sale_price * rate, 2)
    return {
        "referral_fee": fee,
        "rate": f"{rate:.0%}",
        "category": category,
        "sale_price": sale_price,
    }


@mcp.tool()
def calculate_prep_cost(
    weight_lbs: float = 1.0,
    size_tier: str = "standard",
    needs_poly_bag: bool = False,
    needs_bubble_wrap: bool = False,
) -> dict:
    """
    Calculate AMSCO prep center cost per unit (Huntley, IL).

    Amazon's FBA prep service was discontinued January 2026.
    AMSCO Prep is the standard 3PL for FBA sellers in the Chicago area.

    Args:
        weight_lbs: Unit weight in pounds for inbound shipping cost.
        size_tier: 'standard' or 'oversize'.
        needs_poly_bag: Whether unit requires poly bag ($0.50).
        needs_bubble_wrap: Whether unit requires bubble wrap ($0.75).

    Returns:
        dict with total prep cost and itemized breakdown.
    """
    base = PREP_COST_CONFIG["oversize_prep"] if size_tier == "oversize" else PREP_COST_CONFIG["standard_prep"]
    poly = PREP_COST_CONFIG["poly_bag"] if needs_poly_bag else 0
    bubble = PREP_COST_CONFIG["bubble_wrap"] if needs_bubble_wrap else 0
    label = PREP_COST_CONFIG["label_per_unit"]
    inbound = round(PREP_COST_CONFIG["inbound_shipping_per_lb"] * weight_lbs, 4)
    total = round(base + poly + bubble + label + inbound, 4)

    return {
        "total_prep_cost": total,
        "breakdown": {
            "base_prep": base,
            "label": label,
            "inbound_shipping": inbound,
            "poly_bag": poly,
            "bubble_wrap": bubble,
        },
        "prep_center": "AMSCO Prep, Huntley IL",
    }


@mcp.tool()
def calculate_total_fees(
    sale_price: float,
    weight_oz: float = 16.0,
    size_tier: str = "standard_size",
    category: str = "Home & Kitchen",
    weight_lbs: float = 1.0,
    needs_poly_bag: bool = False,
    needs_bubble_wrap: bool = False,
) -> dict:
    """
    Calculate all-in Amazon FBA fees for a product — fulfillment, referral, prep, and placement.

    Use this to determine how much of the sale price goes to fees before calculating profit.

    Args:
        sale_price: Amazon sale price in dollars.
        weight_oz: Product weight in ounces.
        size_tier: 'small_standard', 'standard_size', or 'large_bulky'.
        category: Amazon product category.
        weight_lbs: Weight in pounds for prep/shipping cost.
        needs_poly_bag: Whether unit needs poly bag.
        needs_bubble_wrap: Whether unit needs bubble wrap.

    Returns:
        dict with total_fees, fee_breakdown, and fees_as_pct_of_sale_price.
    """
    fba = get_fba_fee(weight_oz, size_tier)["fba_fee"]
    referral = calculate_referral_fee(category, sale_price)["referral_fee"]
    prep = calculate_prep_cost(weight_lbs, "oversize" if size_tier == "large_bulky" else "standard", needs_poly_bag, needs_bubble_wrap)["total_prep_cost"]
    placement = INBOUND_PLACEMENT_FEES.get(size_tier, INBOUND_PLACEMENT_FEES["standard_size"])
    total = round(fba + referral + prep + placement, 2)

    return {
        "total_fees": total,
        "fee_breakdown": {
            "fba_fulfillment": fba,
            "referral_fee": referral,
            "prep_cost": prep,
            "inbound_placement_fee": placement,
        },
        "sale_price": sale_price,
        "fees_as_pct_of_sale": f"{(total / sale_price * 100):.1f}%" if sale_price > 0 else "N/A",
        "revenue_after_fees": round(sale_price - total, 2),
    }


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="http", host="0.0.0.0", port=port)
