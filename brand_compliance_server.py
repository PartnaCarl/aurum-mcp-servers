"""
brand_compliance_server.py — AURUM Brand Compliance Checker MCP Server

Check any brand against Amazon gating status and IP complaint risk
before buying wholesale inventory. Saves sellers from account suspensions.

Sources:
  - Amazon Seller Central gating thread aggregation (category approval lists)
  - SP-API Brand Registry enforcement patterns
  - Public counterfeit complaint records on seller forums
  - Known Manufacturer Authorized Reseller Program (MAP) enforcement

Tools:
  - check_brand: Single brand lookup → GATED / IP_RISKY / COMMINGLING_RISK / CLEAR
  - check_brands_batch: Check a list of brands at once (for wholesale list review)
"""

from fastmcp import FastMCP
from typing import List

mcp = FastMCP("Brand Compliance Checker")

# ---------------------------------------------------------------------------
# Brand lists — all entries are lowercase for case-insensitive matching.
# Dedupe is enforced by Python set semantics.
# ---------------------------------------------------------------------------

GATED_BRANDS = {
    # --- Electronics / Tech (Amazon category approval required) ---
    "apple", "samsung", "sony", "bose", "beats", "jbl", "lg", "panasonic",
    "canon", "nikon", "gopro", "ring", "nest", "intel", "nvidia", "amd",
    "qualcomm", "tp-link", "netgear", "linksys", "eero", "garmin", "fitbit",
    "sonos", "logitech", "razer", "microsoft", "xbox", "playstation", "nintendo",
    "roku", "fire tv", "anker", "belkin", "kensington", "philips hue",
    "dell", "hp", "lenovo", "asus", "acer", "msi", "corsair", "steelseries",
    "huawei", "xiaomi", "oneplus", "motorola", "nokia", "dji", "parrot",
    "ecobee", "honeywell", "august", "schlage", "yale", "arlo", "wyze",
    "lutron", "amazon echo", "google nest", "eufy",

    # --- Apparel / Footwear (Brand Registry, aggressive enforcement) ---
    "nike", "adidas", "under armour", "new balance", "reebok", "puma",
    "asics", "brooks", "saucony", "hoka", "on running", "allbirds",
    "vans", "converse", "crocs", "birkenstock", "ugg", "timberland",
    "north face", "columbia", "patagonia", "arc'teryx", "marmot",
    "mountain hardwear", "lululemon", "athleta", "fabletics", "alo yoga",
    "vuori", "ralph lauren", "polo ralph lauren", "tommy hilfiger",
    "calvin klein", "gucci", "louis vuitton", "coach", "kate spade",
    "michael kors", "tory burch", "rag & bone", "ag jeans", "7 for all mankind",
    "levi's", "levis", "wrangler", "lee", "carhartt", "dickies", "champion",
    "fruit of the loom", "hanes", "gildan", "peter millar", "brooks brothers",
    "theory", "vince", "free people", "anthropologie", "reformation",
    "spanx", "wolford", "tumi", "samsonite", "away", "monos", "rimowa",
    "briggs & riley", "filson", "moncler", "canada goose", "parajumpers",
    "barbour",

    # --- Sunglasses / Eyewear (EssilorLuxottica + Kering — very aggressive) ---
    "ray-ban", "rayban", "oakley", "persol", "costa del mar", "maui jim",
    "warby parker", "prada eyewear", "versace eyewear", "tom ford eyewear",
    "armani eyewear", "miu miu eyewear", "smith optics", "julbo",
    "serengeti", "wiley x", "bolle", "native eyewear", "dragon alliance",

    # --- Toys / Entertainment (major IP, heavily enforced) ---
    "lego", "hasbro", "mattel", "fisher-price", "barbie", "hot wheels",
    "nerf", "my little pony", "play-doh", "melissa & doug", "playmobil",
    "bruder", "schleich", "thomas & friends", "paw patrol", "peppa pig",
    "bluey", "squishmallows", "jellycat", "gund", "ty", "pokemon", "funko",
    "disney", "marvel", "star wars", "pixar", "nickelodeon", "sesame street",
    "warner bros", "dc comics", "sanrio", "hello kitty", "crayola",
    "magic the gathering", "wizards of the coast", "games workshop",
    "warhammer", "hot toys", "neca", "mcfarlane", "super7",

    # --- Appliances / Household ---
    "dyson", "shark", "irobot", "roomba", "bissell", "hoover", "miele",
    "kitchenaid", "vitamix", "blendtec", "instant pot", "ninja", "keurig",
    "nespresso", "breville", "cuisinart", "hamilton beach", "oxo",
    "rubbermaid", "tupperware", "pyrex", "le creuset", "staub", "lodge",
    "all-clad", "calphalon", "tramontina", "made in", "our place",
    "caraway", "great jones", "misen", "zojirushi", "tiger", "cosori",
    "brita", "simplehuman", "fellow", "chemex", "aeropress", "bodum",

    # --- Health & Beauty (Amazon Beauty gating, Sephora-style brands) ---
    "neutrogena", "olay", "cerave", "cetaphil", "la roche-posay", "vichy",
    "aveeno", "eucerin", "nivea", "jergens", "aquaphor", "dove", "old spice",
    "axe", "degree", "secret", "herbal essences", "pantene", "head & shoulders",
    "garnier", "l'oreal", "loreal", "matrix", "redken", "pureology",
    "kerastase", "olaplex", "k18", "living proof", "oribe", "bumble and bumble",
    "moroccanoil", "ouai", "davines", "r+co", "mielle", "shea moisture",
    "cantu", "carol's daughter", "pattern beauty", "estee lauder", "mac",
    "clinique", "bobbi brown", "too faced", "urban decay", "nars",
    "laura mercier", "tarte", "benefit", "stila", "anastasia beverly hills",
    "charlotte tilbury", "pat mcgrath", "huda beauty", "rare beauty",
    "fenty beauty", "haus labs", "kylie cosmetics", "kkw beauty", "morphe",
    "colourpop", "elf", "physicians formula", "nyx", "maybelline", "revlon",
    "covergirl", "milani", "wet n wild", "iconic london", "glow recipe",
    "drunk elephant", "sunday riley", "tatcha", "the ordinary", "paula's choice",
    "pixi", "hero cosmetics", "supergoop", "coola", "eltamd", "beautycounter",
    "tula", "dr. dennis gross", "dr. brandt", "perricone md", "philosophy",
    "laneige", "innisfree", "cosrx", "beauty of joseon", "anua", "klairs",
    "missha", "etude house", "tony moly", "mediheal", "dr. jart+", "peach & lily",
    "aveda", "paul mitchell", "wella", "schwarzkopf", "tigi", "joico",
    "biolage", "nioxin",

    # --- Supplements / OTC (FDA-adjacent, counterfeit-heavy) ---
    "optimum nutrition", "muscle milk", "premier protein", "orgain", "vega",
    "garden of life", "ancient nutrition", "bulletproof", "onnit", "thorne",
    "pure encapsulations", "klaire labs", "designs for health", "metagenics",
    "nordic naturals", "carlson labs", "new chapter", "solgar", "now foods",
    "jarrow", "life extension", "doctor's best", "natrol", "nature made",
    "nature's bounty", "centrum", "one a day", "olly", "hum", "ritual",
    "care/of", "vitafusion", "emergen-c", "airborne", "zarbee's", "zicam",
    "tylenol", "advil", "motrin", "aleve", "bayer", "excedrin", "pepto-bismol",
    "imodium", "pepcid", "prilosec", "nexium", "tums", "rolaids", "claritin",
    "zyrtec", "allegra", "benadryl", "sudafed", "mucinex", "delsym",
    "robitussin", "vicks", "halls", "liquid iv", "nuun", "propel", "celsius",
    "body armor", "fairlife", "horizon organic",

    # --- Grocery / Snacks / Beverage (brand-gated) ---
    "nestle", "kellogg's", "kelloggs", "general mills", "post", "quaker",
    "cheerios", "oreo", "chips ahoy", "ritz", "wheat thins", "triscuit",
    "goldfish", "pepperidge farm", "keebler", "pepsi", "coca-cola", "coke",
    "dr pepper", "mountain dew", "sprite", "gatorade", "powerade", "red bull",
    "monster", "rockstar", "bang energy", "vitaminwater", "smartwater",
    "aquafina", "dasani", "voss", "fiji", "evian", "san pellegrino", "perrier",
    "lacroix", "bubbly", "spindrift", "olipop", "poppi", "essentia",
    "chobani", "fage", "siggi's", "oikos", "yoplait", "tillamook", "kerrygold",
    "kraft", "velveeta", "philadelphia", "heinz", "hunt's", "del monte",
    "stouffer's", "lean cuisine", "healthy choice", "amy's kitchen", "digiorno",
    "hot pockets", "eggo", "pillsbury", "betty crocker", "duncan hines",
    "ghirardelli", "lindt", "toblerone", "ferrero", "nutella", "godiva",
    "hershey's", "reese's", "m&m's", "snickers", "twix", "kit kat", "mars",
    "twizzlers", "skittles", "starburst", "mentos", "altoids", "extra",
    "trident", "haribo", "sour patch kids", "swedish fish",

    # --- Pet Supplies (brand-gated) ---
    "purina", "pedigree", "iams", "blue buffalo", "hill's", "royal canin",
    "nutro", "wellness", "orijen", "acana", "merrick", "taste of the wild",
    "stella & chewy's", "primal", "instinct", "freshpet", "greenies",
    "temptations", "milk-bone", "kong", "nylabone", "benebone", "chuckit",
    "frontline", "advantage", "seresto", "capstar", "nexgard", "heartgard",
    "simparica", "bravecto", "whiskas", "fancy feast", "friskies", "sheba",
    "meow mix", "tidy cats", "fresh step", "world's best cat litter",

    # --- Automotive / Parts (counterfeit-heavy, brand-gated) ---
    "mobil 1", "castrol", "valvoline", "pennzoil", "shell helix", "royal purple",
    "amsoil", "lucas oil", "sta-bil", "stp", "seafoam", "3m", "rain-x",
    "armor all", "meguiar's", "chemical guys", "griot's garage",
    "adam's polishes", "turtle wax", "mothers", "sonax", "autoglym",
    "bosch", "ngk", "denso", "ac delco", "k&n", "fram", "wix", "purolator",
    "mann filter", "mahle", "thule", "yakima", "rhino-rack", "pioneer car",
    "alpine", "kenwood", "jvc", "rockford fosgate", "jl audio", "kicker",
    "focal", "hertz audio", "audison",

    # --- Pro Audio / Studio (gated, DJ/pro equipment) ---
    "shure", "sennheiser", "audio-technica", "neumann", "akg", "rode",
    "blue microphones", "electro-voice", "beyerdynamic", "warm audio",
    "universal audio", "focusrite", "presonus", "motu", "rme",
    "antelope audio", "avid", "native instruments", "ableton", "steinberg",
    "behringer", "mackie", "allen & heath", "qsc", "jbl professional",
    "bose professional", "d&b audiotechnik", "l-acoustics", "meyer sound",
    "adam audio", "genelec", "hifiman", "audeze", "klipsch", "kef",
    "polk audio", "definitive technology", "mcintosh", "mark levinson",
    "pioneer dj", "denon dj", "numark", "rane", "serato",

    # --- Luxury / Watches / Jewelry (high-gate, high-IP) ---
    "hermes", "chanel", "prada", "dior", "fendi", "valentino", "versace",
    "balenciaga", "saint laurent", "ysl", "bottega veneta", "celine", "loewe",
    "goyard", "burberry", "ferragamo", "jimmy choo", "christian louboutin",
    "tod's", "zegna", "loro piana", "brunello cucinelli", "cartier",
    "tiffany", "van cleef", "bulgari", "bvlgari", "harry winston", "chopard",
    "piaget", "vacheron constantin", "patek philippe", "audemars piguet",
    "rolex", "omega", "breitling", "tag heuer", "hublot", "iwc", "panerai",
    "jaeger-lecoultre", "longines", "tissot", "oris", "movado", "shinola",
    "montblanc", "s.t. dupont",

    # --- Hydration / Outdoor Drinkware (Brand Registry enforcement) ---
    "yeti", "rtic", "hydroflask", "hydro flask", "stanley", "contigo",
    "thermos", "owala", "corkcicle", "simple modern", "miir", "camelbak",
    "s'well", "bkr", "klean kanteen", "nalgene", "brumate", "igloo",
    "coleman", "otterbox", "pelican",

    # --- Baby / Juvenile (gated, IP-aggressive) ---
    "nuna", "doona", "cybex", "uppababy", "stokke", "ergobaby", "babybjorn",
    "4moms", "britax", "graco", "chicco", "maxi-cosi", "evenflo",
    "baby jogger", "bugaboo", "mima", "silver cross", "orbit baby",
}

# Subset of GATED_BRANDS with known aggressive IP/MAP enforcement history.
# Even if a seller ungates, the listing is high-risk for takedown.
IP_RISKY_BRANDS = {
    "apple", "dyson", "shark", "irobot", "lego", "disney", "marvel",
    "star wars", "pokemon", "nike", "adidas", "lululemon", "north face",
    "ugg", "gucci", "louis vuitton", "chanel", "hermes", "prada", "dior",
    "coach", "beats", "bose", "sonos", "yeti", "hydroflask", "hydro flask",
    "stanley", "owala", "ray-ban", "rayban", "oakley", "persol",
    "costa del mar", "maui jim", "olaplex", "k18", "kerastase", "redken",
    "supreme", "rolex", "patek philippe", "audemars piguet", "cartier",
    "tiffany", "canada goose", "moncler", "arc'teryx", "nuna", "doona",
    "cybex", "uppababy", "stokke", "bugaboo", "pelican", "garmin",
    "gopro", "dji", "microsoft", "nintendo", "playstation", "xbox",
    "sony playstation",
}

# High counterfeit prevalence — not always gated but commingling will
# mix genuine units with fakes. One complaint hits your account regardless.
# FNSKU labeling is mandatory.
COMMINGLING_RISK_BRANDS = {
    "nike", "adidas", "ugg", "north face", "gucci", "louis vuitton",
    "beats", "sony", "bose", "apple", "samsung", "vitamix", "yeti",
    "rtic", "hydroflask", "hydro flask", "owala", "stanley", "contigo",
    "lululemon", "olaplex", "k18", "kerastase", "ray-ban", "rayban",
    "oakley", "maui jim", "rolex", "cartier", "tiffany", "pokemon",
    "funko", "lego", "magic the gathering", "optimum nutrition",
    "muscle milk", "bang energy", "celsius", "red bull", "monster",
    "3m", "k&n", "mobil 1", "castrol", "bosch", "ngk",
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
      GATED           — Amazon requires approval to sell. Do not source without applying first.
      IP_RISKY        — High IP complaint history. Even if ungated, risk of suspension.
      COMMINGLING_RISK — Not gated, but counterfeit prevalence is high. Use FNSKU labels only.
      CLEAR           — No known gating or IP issues. Normal due diligence still applies.

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
