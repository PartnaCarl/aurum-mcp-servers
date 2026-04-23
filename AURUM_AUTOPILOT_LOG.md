# AURUM Autopilot Log

**Started:** 2026-04-23
**Branch:** `feature/autopilot-cleanup`
**Operator:** Claude (autonomous mode — no check-ins)

---

## Scope ingested from prompt

| Item | Status at start | Action taken |
|---|---|---|
| Fix sku_scorer_server.py bugs (double `net_margin_pct`, no input validation, duplicate `days_covered` calc) | All three bugs confirmed in file | Fix |
| Write fba_fee_calculator_server.py | **Already exists** with all 4 tools (get_fba_fee, calculate_referral_fee, calculate_prep_cost, calculate_total_fees). Prompt is stale on this | Verify only |
| Expand brand_compliance_server.py to 400+ brands | Currently ~70 brands | Expand, fix Ray-Ban, add 5 categories |
| Fix Ray-Ban → IP_RISKY | Confirmed: "rayban" is only in COMMINGLING_RISK_BRANDS | Move to IP_RISKY_BRANDS |
| tests/ pytest suite | `test_servers.py` exists as ad-hoc script, no `tests/` dir | Restructure into tests/ |
| landing.html (Vantage tokens, 3 pricing cards) | `index.html` exists (4.6KB) — check before overwriting | Build fresh `landing.html` |
| DEPLOY.md | Not present | Write |
| Git workflow | On `main` with untracked `.agents/`, `.claude/`, `skills-lock.json` | New branch `feature/autopilot-cleanup` |

## Stale items in prompt (dropped)

- Instruction to "write" `fba_fee_calculator_server.py` — file already exists and conforms. Verified only.

## Decisions log

(appended as work proceeds)
