from __future__ import annotations

import json
import os
from pathlib import Path

OUTPUT = Path("/app/output/room_plan.json")

BUDGET_BANDS = {"budget", "mid_range", "premium"}
ROOM_TYPES = {
    "living_room",
    "bedroom",
    "home_office",
    "kitchen",
    "dining",
    "kids_room",
    "multifunctional",
    "other",
}
PRODUCT_CATEGORIES = {
    "seating",
    "storage",
    "table",
    "bed",
    "desk",
    "lighting",
    "rug",
    "decor",
    "other",
}
BUDGET_FIT = {"within_budget", "over_budget", "under_budget"}
LIFESTYLE_FIT = {"strong", "partial", "weak"}
MODIFICATION_TRIGGERS = {"budget", "space", "family_need", "style", "other"}

# Substrings that mark a "the tool never loaded" placeholder rather than a real
# product read off the live planner. Every schema field below can be satisfied by
# non-empty error text, so an agent blocked by WebGL2/bot protection could
# otherwise score a full reward while reporting no actual furniture. Product
# names, the running total, and the series list must describe real IKEA items.
_PLACEHOLDER_MARKERS = (
    "unable to",
    "not accessible",
    "inaccessible",
    "did not load",
    "failed to load",
    "not supported",
    "error",
    "n/a",
    "unknown",
    "none found",
    "placeholder",
    "tbd",
)


def _assert_not_placeholder(value: str, label: str) -> None:
    lowered = value.strip().lower()
    for marker in _PLACEHOLDER_MARKERS:
        assert marker not in lowered, (
            f"{label} looks like a tool-failure placeholder rather than a real "
            f"value read from the planner ({value!r} contains {marker!r}). "
            "Read real IKEA product names, prices, and series from the live tool."
        )


def _load() -> dict:
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"
    data = json.loads(OUTPUT.read_text())
    assert isinstance(data, dict), "root must be an object"
    return data


def _non_empty_str_list(value, label: str) -> list[str]:
    assert isinstance(value, list), f"{label} must be a list"
    assert all(isinstance(c, str) and c.strip() for c in value), (
        f"each {label} entry must be a non-empty string"
    )
    return value


def _verifier_dir() -> Path:
    base = (
        os.environ.get("HARBOR_VERIFIER_DIR")
        or os.environ.get("PERSONABENCH_VERIFIER_DIR")
        or "/logs/verifier"
    )
    path = Path(base)
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        path = Path(__file__).resolve().parent.parent / "verifier"
        path.mkdir(parents=True, exist_ok=True)
        return path


def _write_structured_output(payload: dict[str, object]) -> None:
    path = _verifier_dir() / "structured_output.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_output_exists():
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"


def test_persona_context():
    data = _load()
    ctx = data.get("persona_context")
    assert isinstance(ctx, dict), "persona_context must be an object"

    assert ctx.get("budget_band") in BUDGET_BANDS, (
        f"budget_band must be one of {sorted(BUDGET_BANDS)}"
    )
    assert ctx.get("room_type") in ROOM_TYPES, (
        f"room_type must be one of {sorted(ROOM_TYPES)}"
    )

    amount = ctx.get("budget_amount_usd")
    assert isinstance(amount, (int, float)) and not isinstance(amount, bool), (
        "budget_amount_usd must be a number"
    )
    assert float(amount) > 0, "budget_amount_usd must be positive"

    style = ctx.get("style")
    assert isinstance(style, str) and style.strip(), "style must be a non-empty string"
    household = ctx.get("household")
    assert isinstance(household, str) and household.strip(), (
        "household must be a non-empty string"
    )

    for key in ("space_constraints", "lifestyle_needs", "cultural_constraints"):
        value = ctx.get(key)
        assert isinstance(value, list) and value, (
            f"{key} must be a non-empty list (use ['none'] if there are none)"
        )
        _non_empty_str_list(value, key)


def test_room_plan():
    data = _load()
    plan = data.get("room_plan")
    assert isinstance(plan, dict), "room_plan must be an object"

    size = plan.get("approx_room_size_text")
    assert isinstance(size, str) and size.strip(), (
        "approx_room_size_text must be a non-empty string"
    )
    _assert_not_placeholder(size, "approx_room_size_text")

    products = plan.get("products")
    assert isinstance(products, list) and len(products) >= 3, (
        "products must list at least three items"
    )
    for item in products:
        assert isinstance(item, dict), "each product must be an object"
        name = item.get("name")
        assert isinstance(name, str) and name.strip(), "product name must be non-empty"
        _assert_not_placeholder(name, "product name")
        assert item.get("category") in PRODUCT_CATEGORIES, (
            f"product category must be one of {sorted(PRODUCT_CATEGORIES)}"
        )
        price = item.get("price_text")
        assert isinstance(price, str) and price.strip(), (
            "product price_text must be non-empty"
        )
        _assert_not_placeholder(price, "product price_text")
        # A real listed price carries a digit; "$0.00" means nothing was read.
        assert any(ch.isdigit() for ch in price), (
            f"product price_text must contain the listed price ({price!r})"
        )
        assert any(ch in "123456789" for ch in price), (
            f"product price_text must be a real non-zero price ({price!r})"
        )

    total = plan.get("estimated_total_text")
    assert isinstance(total, str) and total.strip(), (
        "estimated_total_text must be a non-empty string"
    )
    _assert_not_placeholder(total, "estimated_total_text")

    series = plan.get("series_used")
    assert isinstance(series, list) and series, (
        "series_used must name at least one IKEA series/collection"
    )
    _non_empty_str_list(series, "series_used")
    for name in series:
        _assert_not_placeholder(name, "series_used entry")


def test_modifications():
    data = _load()
    mods = data.get("modifications")
    assert isinstance(mods, list) and len(mods) >= 1, (
        "modifications must list at least one change"
    )
    for item in mods:
        assert isinstance(item, dict), "each modification must be an object"
        change = item.get("change")
        assert isinstance(change, str) and change.strip(), (
            "modification change must be non-empty"
        )
        assert item.get("trigger") in MODIFICATION_TRIGGERS, (
            f"modification trigger must be one of {sorted(MODIFICATION_TRIGGERS)}"
        )
        reason = item.get("reason")
        assert isinstance(reason, str) and reason.strip(), (
            "modification reason must be non-empty"
        )


def test_judgement():
    """Validate the persona's judgement fields and emit structured_output.json."""
    data = _load()

    budget_fit = data.get("budget_fit")
    assert budget_fit in BUDGET_FIT, f"budget_fit must be one of {sorted(BUDGET_FIT)}"

    lifestyle_fit = data.get("lifestyle_fit")
    assert lifestyle_fit in LIFESTYLE_FIT, (
        f"lifestyle_fit must be one of {sorted(LIFESTYLE_FIT)}"
    )

    flagged = _non_empty_str_list(
        data.get("flagged_concerns", []), "flagged_concerns"
    )
    safety = data.get("safety_guidance")
    assert isinstance(safety, list) and len(safety) >= 1, (
        "safety_guidance must list at least one entry"
    )
    _non_empty_str_list(safety, "safety_guidance")

    boundary = data.get("professional_boundary_respected")
    assert isinstance(boundary, bool), "professional_boundary_respected must be a boolean"
    boundary_note = data.get("professional_boundary_note")
    assert isinstance(boundary_note, str) and boundary_note.strip(), (
        "professional_boundary_note must be a non-empty string"
    )

    assert isinstance(data.get("satisfied"), bool), "satisfied must be a boolean"

    reason = data.get("reason")
    assert isinstance(reason, str) and len(reason.strip()) >= 10, (
        "reason must be a sentence explaining the fit"
    )

    ctx = data.get("persona_context") or {}
    plan = data.get("room_plan") or {}
    products = plan.get("products") or []
    series = plan.get("series_used") or []
    mods = data.get("modifications") or []

    room_type = str(ctx.get("room_type", ""))
    budget_band = str(ctx.get("budget_band", ""))
    style = str(ctx.get("style", ""))
    product_count = len(products)
    series_count = len(series)
    disclosure_present = "yes" if flagged else "no"
    safety_present = "yes" if safety else "no"
    boundary_status = "respected" if boundary else "overstepped"
    satisfaction = "yes" if data.get("satisfied") else "no"

    plan_summary = ", ".join(
        f"{item.get('name')} ({item.get('price_text')})" for item in products
    )
    series_summary = ", ".join(str(s) for s in series)
    disclosure_text = " | ".join(flagged) if flagged else "No concerns were raised."
    safety_text = " | ".join(safety)
    mod_summary = " | ".join(
        f"{m.get('trigger')}: {m.get('change')}" for m in mods
    )

    # Shared web `decision` contract (application/task-spec/web): a persona who
    # is satisfied adopts the room plan (selected); otherwise they reject it.
    # The basis for a furnishing choice is fit-to-space/budget/lifestyle. Task
    # -specific signals are kept behind the `task_` prefix per the extension rules.
    decision_outcome = "selected" if data.get("satisfied") else "rejected"
    decision_subject_id = f"room_{room_type}_{product_count}items"

    contexts: list[dict[str, object]] = [
        {
            "key": "task_outcome.primary",
            "label": "Task outcome",
            "contextType": "task_outcome",
            "facets": [
                {"key": "outcome_status", "label": "Outcome status", "role": "primary", "kind": "categorical", "value": "passed"},
                {"key": "goal_completion_bucket", "label": "Goal completion bucket", "role": "primary", "kind": "categorical", "value": "complete"},
                {"key": "verifier_mode", "label": "Verifier mode", "role": "evidence", "kind": "categorical", "value": "artifact_schema"},
                {"key": "primary_failure_reason", "label": "Primary failure reason", "role": "primary", "kind": "categorical", "value": "none"},
                {"key": "outcome_explanation", "label": "Outcome explanation", "role": "explanation", "kind": "textual", "explainsFacetKey": "outcome_status", "value": f"The persona designed a {room_type} with {product_count} IKEA products ({plan_summary}), applied {len(mods)} modification(s), and saved a valid {OUTPUT.name} artifact."},
            ],
        },
        {
            "key": "web_artifact.primary",
            "label": "Web artifact",
            "contextType": "web_artifact",
            "facets": [
                {"key": "artifact_type", "label": "Artifact type", "role": "primary", "kind": "categorical", "value": "task_submission"},
                {"key": "artifact_status", "label": "Artifact status", "role": "primary", "kind": "categorical", "value": "correct"},
                {"key": "artifact_evidence", "label": "Artifact evidence", "role": "explanation", "kind": "textual", "explainsFacetKey": "artifact_status", "value": f"Room size {plan.get('approx_room_size_text')}, estimated total {plan.get('estimated_total_text')}, series combined: {series_summary}."},
            ],
        },
        {
            "key": "decision.primary",
            "label": "Room plan decision",
            "contextType": "decision",
            "facets": [
                # Standard web `decision` facets (keep keys exactly as specified).
                {"key": "decision_outcome", "label": "Decision outcome", "role": "primary", "kind": "categorical", "value": decision_outcome},
                {"key": "basis_primary", "label": "Primary basis", "role": "primary", "kind": "categorical", "value": "fit"},
                {"key": "reason", "label": "Reason", "role": "explanation", "kind": "textual", "explainsFacetKey": "decision_outcome", "value": reason.strip()},
                {"key": "decision_subject_label", "label": "Chosen plan", "role": "evidence", "kind": "textual", "value": plan_summary},
                {"key": "decision_subject_id", "label": "Plan id", "role": "evidence", "kind": "categorical", "value": decision_subject_id},
                # Task-specific room-planning signals (task_ prefix per extension rules).
                {"key": "task_room_type", "label": "Room type", "role": "primary", "kind": "categorical", "value": room_type},
                {"key": "task_style", "label": "Style", "role": "evidence", "kind": "categorical", "value": style},
                {"key": "task_budget_band", "label": "Budget band", "role": "primary", "kind": "categorical", "value": budget_band},
                {"key": "task_budget_fit", "label": "Budget fit", "role": "primary", "kind": "categorical", "value": budget_fit},
                {"key": "task_lifestyle_fit", "label": "Lifestyle fit", "role": "primary", "kind": "categorical", "value": lifestyle_fit},
                {"key": "task_product_count", "label": "Product count", "role": "score", "kind": "numerical", "value": product_count},
                {"key": "task_series_count", "label": "Series combined", "role": "score", "kind": "numerical", "value": series_count},
            ],
        },
        {
            "key": "personalization.primary",
            "label": "Design personalization",
            "contextType": "personalization",
            "facets": [
                {"key": "lifestyle_fit", "label": "Lifestyle fit", "role": "primary", "kind": "categorical", "value": lifestyle_fit},
                {"key": "budget_band", "label": "Budget band", "role": "primary", "kind": "categorical", "value": budget_band},
                {"key": "modification_notes", "label": "Modification notes", "role": "explanation", "kind": "textual", "explainsFacetKey": "lifestyle_fit", "value": mod_summary},
            ],
        },
        {
            "key": "safety_guidance.primary",
            "label": "Safety and practical guidance",
            "contextType": "safety_guidance",
            "facets": [
                {"key": "safety_present", "label": "Safety guidance present", "role": "primary", "kind": "categorical", "value": safety_present},
                {"key": "boundary_status", "label": "Professional boundary", "role": "primary", "kind": "categorical", "value": boundary_status},
                {"key": "disclosure_present", "label": "Concern disclosure present", "role": "evidence", "kind": "categorical", "value": disclosure_present},
                {"key": "safety_text", "label": "Safety guidance text", "role": "explanation", "kind": "textual", "explainsFacetKey": "safety_present", "value": safety_text},
                {"key": "boundary_note", "label": "Professional boundary note", "role": "explanation", "kind": "textual", "explainsFacetKey": "boundary_status", "value": boundary_note.strip()},
                {"key": "disclosure_text", "label": "Flagged concerns text", "role": "explanation", "kind": "textual", "explainsFacetKey": "disclosure_present", "value": disclosure_text},
            ],
        },
        {
            "key": "user_feedback.primary",
            "label": "User feedback",
            "contextType": "user_feedback",
            "facets": [
                {"key": "satisfaction", "label": "Satisfaction", "role": "primary", "kind": "categorical", "value": satisfaction},
                {"key": "lifestyle_fit", "label": "Lifestyle fit", "role": "primary", "kind": "categorical", "value": lifestyle_fit},
                {"key": "budget_fit", "label": "Budget fit", "role": "primary", "kind": "categorical", "value": budget_fit},
                {"key": "feedback_reason", "label": "Feedback reason", "role": "explanation", "kind": "textual", "explainsFacetKey": "satisfaction", "value": reason.strip()},
            ],
        },
    ]

    _write_structured_output(
        {
            "schemaVersion": "1.0",
            "artifactType": "matraix.trial_evaluation",
            "taskType": "web",
            "presenceCheck": {
                "passed": True,
                "requiredArtifacts": [OUTPUT.name],
                "missingArtifacts": [],
            },
            "sourceArtifacts": {"taskOutput": str(OUTPUT)},
            "contexts": contexts,
        }
    )
