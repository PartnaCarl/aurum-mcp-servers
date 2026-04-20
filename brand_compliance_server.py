"""
brand_compliance_server.py — AURUM Brand Compliance Checker MCP Server

Check any brand against Amazon gating status and IP complaint risk
before buying wholesale inventory. Saves sellers from account suspensions.

Tools:
  - check_brand: Single brand lookup → GATED / IP_RISKY / COMMINGLING_RISK / CLEAR
  - check_brands_batch: Check a list of brands at once (for wholesale list review)
"""

from fastmcp import FastMCP
from typing import List

mcp = FastMCP("Brand Compliance Checker")

# ---------------------------------------------------------------------------
# Brand lists — sourced from Amazon seller community, SP-API gating data,
# and IP complaint history on seller forums.
# ---------------------------------------------------------------------------

GATED_BRANDS = {
    # Electronics / Tech
    "apple", "samsung", "sony", "bose", "beats", "jbl", "lg", "panasonic",
    "canon", "nikon", "gopro", "ring", "nest", "intel", "nvidia",
    # Apparel / Footwear
    "nike", "adidas", "under armour", "new balance", "reebok", "puma",
    "ugg", "timberland", "north face", "columbia", "patagonia", "lululemon",
    "ralph lauren", "tommy hilfiger", "calvin klein", "gucci", "louis vuitton",
    "coach", "kate spade", "michael kors",
    # Toys / Entertainment
    "lego", "hasbro", "mattel", "fisher-price", "barbie", "hot wheels",
    "nerf", "pokemon", "funko", "disney", "marvel", "star wars",
    # Household / Appliances
    "dyson", "shark", "irobot", "kitchenaid", "vitamix", "instant pot",
    "ninja", "keurig", "nespresso", "cuisinart",
    # Health / Beauty
    "neutrogena", "olay", "estee lauder", "lancome", "clinique", "mac",
    "urban decay", "anastasia beverly hills", "charlotte tilbury",
    # Other
    "levi's", "levis", "wrangler", "carhartt", "yeti", "hydroflask", "owala",
    "stanley", "thermos", "contigo",
}

# Brands known for aggressive IP complaints / cease and desist activity
IP_RISKY_BRANDS = {
    "apple", "dyson", "shark", "irobot", "lego", "disney", "nike",
    "adidas", "north face", "ugg", "gucci", "louis vuitton", "coach",
    "beats", "bose", "vitamix", "yeti", "hydroflask",
}

# High counterfeit prevalence — not hard-blocked but flag for FNSKU labeling.
# Amazon's commingling can mix your genuine units with fakes from other sellers.
# One authenticity complaint hits your account regardless of who sold the fake.
COMMINGLING_RISK_BRANDS = {
    "nike", "ugg", "north face", "gucci", "rayban", "beats",
    "vitamix", "yeti", "hydroflask", "owala", "stanley", "lululemon",
}


def _normalize(brand: str) -> str:
    return brand.strip().lower()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def check_brand(brand_name: str) -> dict:
    """
    Check if a brand is gated, IP-risky, or safe to sell on Amazon.

    Use this before purchasing any wholesale inventory to avoid account suspensions,
    IP complaints, and gating violations.

    Status meanings:
      GATED       — Amazon requires approval to sell. Do not source without applying first.
      IP_RISKY    — High IP complaint history. Even if ungated, risk of suspension.
      COMMINGLING — Not gated, but counterfeit prevalence is high. Use FNSKU labels only.
      CLEAR       — No known gating or IP issues. Normal due diligence still applies.

    Args:
        brand_name: Brand name to check (case-insensitive).

    Returns:
        dict with status, risk_level, brand, and recommendation.
    """
    b = _normalize(brand_name)

    if b in IP_RISKY_BRANDS:
        return {
            "brand": brand_name,
            "status": "IP_RISKY",
            "risk_level": "HIGH",
            "is_gated": b in GATED_BRANDS,
            "commingling_risk": b in COMMINGLING_RISK_BRANDS,
            "recommendation": (
                f"{brand_name} has a high history of IP complaints and cease-and-desist actions. "
                "Do not source even if ungated. Account suspension risk is significant."
            ),
        }

    if b in GATED_BRANDS:
        return {
            "brand": brand_name,
            "status": "GATED",
            "risk_level": "MEDIUM",
            "is_gated": True,
            "commingling_risk": b in COMMINGLING_RISK_BRANDS,
            "recommendation": (
                f"{brand_name} requires Amazon seller approval before listing. "
                "Apply for ungating via Seller Central before purchasing inventory."
            ),
        }

    if b in COMMINGLING_RISK_BRANDS:
        return {
            "brand": brand_name,
            "status": "COMMINGLING_RISK",
            "risk_level": "LOW",
            "is_gated": False,
            "commingling_risk": True,
            "recommendation": (
                f"{brand_name} has high counterfeit prevalence. Use FNSKU labels only — "
                "never manufacturer barcode. Commingled inventory can mix with fakes."
            ),
        }

    return {
        "brand": brand_name,
        "status": "CLEAR",
        "risk_level": "NONE",
        "is_gated": False,
        "commingling_risk": False,
        "recommendation": f"{brand_name} has no known gating or IP issues. Standard due diligence applies.",
    }


@mcp.tool()
def check_brands_batch(brand_names: List[str]) -> dict:
    """
    Check a list of brands against Amazon gating and IP risk in one call.

    Use this when reviewing a wholesale price list or supplier catalog.
    Returns a summary plus per-brand results sorted by risk level (highest first).

    Args:
        brand_names: List of brand names to check.

    Returns:
        dict with summary counts and per-brand results.
    """
    results = [check_brand(b) for b in brand_names]

    risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "NONE": 3}
    results.sort(key=lambda r: risk_order.get(r["risk_level"], 9))

    summary = {
        "total_checked": len(results),
        "ip_risky": sum(1 for r in results if r["status"] == "IP_RISKY"),
        "gated": sum(1 for r in results if r["status"] == "GATED"),
        "commingling_risk": sum(1 for r in results if r["status"] == "COMMINGLING_RISK"),
        "clear": sum(1 for r in results if r["status"] == "CLEAR"),
    }

    return {
        "summary": summary,
        "results": results,
        "do_not_source": [r["brand"] for r in results if r["status"] in ("IP_RISKY", "GATED")],
    }


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="http", host="0.0.0.0", port=port)
