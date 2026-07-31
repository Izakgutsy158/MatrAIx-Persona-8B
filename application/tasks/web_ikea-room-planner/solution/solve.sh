#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
from pathlib import Path

output = Path("/app/output/room_plan.json")

# Reference oracle. IKEA's Room Planner is a heavy, anti-bot-protected 3D/WebGL
# design tool, so the oracle does not drive the live planner; it emits a
# schema-valid reference submission for a mid-range family living-room persona to
# exercise the task and verifier contract end to end. Persona agents fill the
# products, prices, and totals from the live tool.
try:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        # Best-effort reachability check; failures are non-fatal for the oracle.
        # The `#<design-id>/<scene-id>` fragment is required; the bare
        # ?roomType=generic URL hangs on "Preparing your room ..." forever.
        page.goto(
            "https://www.ikea.com/us/en/home-design/room/?roomType=generic"
            "#1d9a5bb8-08b5-43aa-ab0c-ff91d92c95f9/0943b0b9-198c-4e74-b287-171db3f4ad35",
            wait_until="domcontentloaded",
            timeout=60_000,
        )
        browser.close()
except Exception:
    pass

payload = {
    "persona_context": {
        "budget_band": "mid_range",
        "budget_amount_usd": 1500,
        "room_type": "living_room",
        "style": "cozy scandinavian",
        "household": "couple with a toddler and a cat",
        "space_constraints": ["small flat", "limited natural light"],
        "lifestyle_needs": ["family with kids", "pets", "entertainment"],
        "cultural_constraints": ["family gathering space"],
    },
    "room_plan": {
        "approx_room_size_text": "3.5 x 4 m",
        "products": [
            {"name": "KIVIK 3-seat sofa", "category": "seating", "price_text": "$799.00"},
            {"name": "LACK coffee table", "category": "table", "price_text": "$49.99"},
            {"name": "BILLY bookcase", "category": "storage", "price_text": "$69.99"},
            {"name": "RINGBLOMMA rug", "category": "rug", "price_text": "$99.00"},
            {"name": "FOTO pendant lamp", "category": "lighting", "price_text": "$34.99"},
        ],
        "estimated_total_text": "$1,052.97",
        "series_used": ["KIVIK", "LACK", "BILLY"],
    },
    "modifications": [
        {
            "change": "Swapped a larger sectional for the KIVIK 3-seat sofa",
            "trigger": "space",
            "reason": "The sectional blocked the walkway to the balcony in a small flat, so a "
            "3-seat sofa left a clear path while still seating the family.",
        },
        {
            "change": "Dropped an accent armchair to stay under $1,500",
            "trigger": "budget",
            "reason": "Removing the POÄNG armchair kept the plan comfortably within the "
            "mid-range budget without losing seating the household actually needs.",
        },
    ],
    "budget_fit": "within_budget",
    "lifestyle_fit": "strong",
    "flagged_concerns": [
        "The open BILLY bookcase is within a toddler's reach; lower shelves should hold "
        "soft or unbreakable items only.",
        "A glass-top coffee table option was avoided because sharp corners are a hazard "
        "with a young child.",
    ],
    "safety_guidance": [
        "Anchor the BILLY bookcase to the wall with the included anti-tip restraint so a "
        "climbing toddler cannot pull it over.",
        "Keep at least ~90 cm of walkway clearance between the sofa and coffee table so the "
        "path to the balcony stays unobstructed.",
        "Choose the rounded-corner coffee-table variant to reduce head-height sharp edges "
        "for the child.",
    ],
    "professional_boundary_respected": True,
    "professional_boundary_note": (
        "The planner suggested nothing structural. I only laid out and furnished the "
        "existing room; I would not move walls, relocate wiring, or commission a formal "
        "certified design without a licensed professional."
    ),
    "satisfied": True,
    "reason": (
        "A cozy scandinavian KIVIK/LACK/BILLY combination fits a small, low-light family "
        "living room within a mid-range $1,500 budget: it seats a couple plus guests for "
        "gatherings, keeps a clear walkway for a toddler and cat, and every tall piece has "
        "a wall-anchoring and hazard plan, so the layout is practical and safe for this "
        "household."
    ),
}
output.write_text(json.dumps(payload, indent=2) + "\n")
PY
