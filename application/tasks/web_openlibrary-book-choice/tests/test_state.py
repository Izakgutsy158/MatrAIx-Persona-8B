from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

OUTPUT = Path("/app/output/book_choice.json")
USER_FEEDBACK = Path("/app/output/user_feedback.json")
BASIS_VALUES = {
    "price",
    "quality",
    "features",
    "convenience",
    "taste",
    "trust",
    "familiarity",
    "novelty",
    "fit",
    "other",
}
EXPLORATION_STYLES = {"compared_multiple", "deep_research"}
SATISFACTION_BUCKETS = {"yes", "partially", "no"}
WORK_ID = re.compile(r"^OL\d+W$")


def _nonempty(value: object, field: str) -> str:
    assert isinstance(value, str) and value.strip(), f"{field} must be non-empty"
    return value.strip()


def _work_id(url: object, field: str) -> str:
    book_url = _nonempty(url, field)
    parsed = urlparse(book_url)
    assert parsed.scheme == "https", f"{field} must use https"
    assert parsed.netloc == "openlibrary.org", f"{field} must use openlibrary.org"
    assert not parsed.query and not parsed.fragment, f"{field} must not contain a query or fragment"
    parts = parsed.path.strip("/").split("/")
    assert len(parts) in (2, 3) and parts[0] == "works", (
        f"{field} must be an Open Library work-detail URL"
    )
    work_id = parts[1]
    assert WORK_ID.fullmatch(work_id), f"{field} contains an invalid work ID"
    return work_id


def _validate_candidate(candidate: object, index: int) -> dict[str, str]:
    assert isinstance(candidate, dict), f"task_options_considered[{index}] must be an object"
    prefix = f"task_options_considered[{index}]"
    book_url = _nonempty(candidate.get("task_book_url"), f"{prefix}.task_book_url")
    work_id = _work_id(book_url, f"{prefix}.task_book_url")
    subject_id = _nonempty(candidate.get("decision_subject_id"), f"{prefix}.decision_subject_id")
    assert subject_id == work_id, f"{prefix}.decision_subject_id must match the URL work ID"
    return {
        "decision_subject_id": subject_id,
        "decision_subject_label": _nonempty(
            candidate.get("decision_subject_label"), f"{prefix}.decision_subject_label"
        ),
        "task_book_url": book_url,
        "task_book_author": _nonempty(
            candidate.get("task_book_author"), f"{prefix}.task_book_author"
        ),
        "task_book_first_published": _nonempty(
            candidate.get("task_book_first_published"),
            f"{prefix}.task_book_first_published",
        ),
        "task_relevance_note": _nonempty(
            candidate.get("task_relevance_note"), f"{prefix}.task_relevance_note"
        ),
    }


def _verifier_dir() -> Path:
    explicit = os.environ.get("HARBOR_VERIFIER_DIR")
    if explicit:
        path = Path(explicit)
        path.mkdir(parents=True, exist_ok=True)
        return path

    container_default = Path("/logs/verifier")
    try:
        container_default.mkdir(parents=True, exist_ok=True)
        return container_default
    except OSError:
        pass

    raise RuntimeError(
        "HARBOR_VERIFIER_DIR is required when running outside a Harbor trial "
        "container. Point it at jobs/<job>/<trial>/verifier for local harness runs."
    )


def _write_structured_output(payload: dict[str, object]) -> None:
    path = _verifier_dir() / "structured_output.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load() -> dict[str, object]:
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"
    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "book_choice.json root must be an object"
    return data


def _load_user_feedback() -> dict[str, object] | None:
    if not USER_FEEDBACK.is_file():
        return None
    data = json.loads(USER_FEEDBACK.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "user_feedback.json root must be an object"

    need = data.get("needConstraintSatisfaction")
    assert need in SATISFACTION_BUCKETS, "needConstraintSatisfaction must use a supported bucket"
    preference = data.get("personalPreferenceSatisfaction")
    assert preference in SATISFACTION_BUCKETS, (
        "personalPreferenceSatisfaction must use a supported bucket"
    )
    reason = _nonempty(data.get("reason"), "feedback reason")

    overall = data.get("overallExperienceRating")
    assert isinstance(overall, (int, float)), "overallExperienceRating must be numeric"
    overall = int(round(float(overall)))
    assert 1 <= overall <= 10, "overallExperienceRating must be between 1 and 10"

    payload: dict[str, object] = {
        "need_constraint_satisfaction": need,
        "personal_preference_satisfaction": preference,
        "overall_experience_rating": overall,
        "feedback_reason": reason,
    }

    for source_key, target_key in (("trustLevel", "trust_level"), ("effortRating", "effort_rating")):
        value = data.get(source_key)
        if value is not None:
            assert isinstance(value, (int, float)), f"{source_key} must be numeric"
            value = int(round(float(value)))
            assert 1 <= value <= 10, f"{source_key} must be between 1 and 10"
            payload[target_key] = value

    clarity = data.get("clarityOfNextStep")
    if clarity is not None:
        assert isinstance(clarity, bool), "clarityOfNextStep must be boolean"
        payload["clarity_of_next_step"] = "true" if clarity else "false"

    return payload


def _execution_contexts(
    *, subject_id: str, subject_label: str, candidate_count: int
) -> list[dict[str, object]]:
    return [
        {
            "key": "task_outcome.primary",
            "label": "Task outcome",
            "contextType": "task_outcome",
            "facets": [
                {
                    "key": "outcome_status",
                    "label": "Outcome status",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "passed",
                },
                {
                    "key": "goal_completion_ratio",
                    "label": "Goal completion ratio",
                    "role": "score",
                    "kind": "numerical",
                    "value": 1.0,
                },
                {
                    "key": "goal_completion_bucket",
                    "label": "Goal completion bucket",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "complete",
                },
                {
                    "key": "verifier_mode",
                    "label": "Verifier mode",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": "artifact_exact",
                },
                {
                    "key": "primary_failure_reason",
                    "label": "Primary failure reason",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "none",
                },
                {
                    "key": "outcome_explanation",
                    "label": "Outcome explanation",
                    "role": "explanation",
                    "kind": "textual",
                    "value": (
                        f"The user selected {subject_label} after recording "
                        f"{candidate_count} distinct Open Library candidates."
                    ),
                },
                {
                    "key": "completion_evidence",
                    "label": "Completion evidence",
                    "role": "evidence",
                    "kind": "textual",
                    "value": (
                        f"Saved {OUTPUT.name} with decision subject {subject_id} and "
                        f"{candidate_count} validated candidate records."
                    ),
                },
            ],
        },
        {
            "key": "web_artifact.primary",
            "label": "Web artifact",
            "contextType": "web_artifact",
            "facets": [
                {
                    "key": "artifact_type",
                    "label": "Artifact type",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "selection",
                },
                {
                    "key": "artifact_status",
                    "label": "Artifact status",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "correct",
                },
                {
                    "key": "artifact_subject_label",
                    "label": "Artifact subject label",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": subject_label,
                },
                {
                    "key": "artifact_subject_id",
                    "label": "Artifact subject id",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": subject_id,
                },
                {
                    "key": "artifact_evidence",
                    "label": "Artifact evidence",
                    "role": "explanation",
                    "kind": "textual",
                    "value": "The selection metadata is internally consistent with the candidate list.",
                },
            ],
        },
        {
            "key": "web_interaction.primary",
            "label": "Web interaction",
            "contextType": "web_interaction",
            "facets": [
                {
                    "key": "navigation_path_type",
                    "label": "Navigation path type",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "compare_then_commit",
                },
                {
                    "key": "web_interaction_notes",
                    "label": "Web interaction notes",
                    "role": "explanation",
                    "kind": "textual",
                    "value": (
                        "The submission records a compare-then-commit path with "
                        f"{candidate_count} distinct book candidates."
                    ),
                },
            ],
        },
    ]


def test_output_exists() -> None:
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"


def test_output_schema() -> None:
    data = _load()
    feedback = _load_user_feedback()

    subject_id = _nonempty(data.get("decision_subject_id"), "decision_subject_id")
    subject_label = _nonempty(data.get("decision_subject_label"), "decision_subject_label")
    assert data.get("decision_outcome") == "selected", "decision_outcome must be selected"

    basis_primary = data.get("basis_primary")
    assert basis_primary in BASIS_VALUES, "basis_primary must use a supported bucket"
    basis_secondary = data.get("basis_secondary")
    if basis_secondary is not None:
        assert basis_secondary in BASIS_VALUES, "basis_secondary must use a supported bucket"
        assert basis_secondary != basis_primary, "basis_secondary must differ from basis_primary"

    exploration_style = data.get("exploration_style")
    assert exploration_style in EXPLORATION_STYLES, (
        "exploration_style must be compared_multiple or deep_research"
    )
    reason = _nonempty(data.get("reason"), "reason")

    selected_url = _nonempty(data.get("task_book_url"), "task_book_url")
    selected_work_id = _work_id(selected_url, "task_book_url")
    assert subject_id == selected_work_id, "decision_subject_id must match task_book_url work ID"
    selected_author = _nonempty(data.get("task_book_author"), "task_book_author")
    selected_first_published = _nonempty(
        data.get("task_book_first_published"), "task_book_first_published"
    )

    raw_candidates = data.get("task_options_considered")
    assert isinstance(raw_candidates, list), "task_options_considered must be an array"
    assert len(raw_candidates) >= 3, "task_options_considered must contain at least three books"
    candidates = [_validate_candidate(item, index) for index, item in enumerate(raw_candidates)]

    ids = [candidate["decision_subject_id"] for candidate in candidates]
    urls = [candidate["task_book_url"] for candidate in candidates]
    assert len(ids) == len(set(ids)), "candidate work IDs must be distinct"
    assert len(urls) == len(set(urls)), "candidate book URLs must be distinct"

    selected_matches = [
        candidate for candidate in candidates if candidate["decision_subject_id"] == subject_id
    ]
    assert len(selected_matches) == 1, "selected book must appear exactly once in candidate list"
    selected = selected_matches[0]
    assert selected["decision_subject_label"] == subject_label, "selected book title must match"
    assert selected["task_book_url"] == selected_url, "selected book URL must match"
    assert selected["task_book_author"] == selected_author, "selected book author must match"
    assert selected["task_book_first_published"] == selected_first_published, (
        "selected book first-published year must match"
    )

    source_artifacts: dict[str, object] = {"taskOutput": str(OUTPUT)}
    contexts = _execution_contexts(
        subject_id=subject_id,
        subject_label=subject_label,
        candidate_count=len(candidates),
    )

    decision_facets: list[dict[str, object]] = [
        {
            "key": "decision_outcome",
            "label": "Decision outcome",
            "role": "primary",
            "kind": "categorical",
            "value": "selected",
        },
        {
            "key": "basis_primary",
            "label": "Primary basis",
            "role": "primary",
            "kind": "categorical",
            "value": basis_primary,
        },
        {
            "key": "reason",
            "label": "Reason",
            "role": "explanation",
            "kind": "textual",
            "explainsFacetKey": "decision_subject_label",
            "value": reason,
        },
        {
            "key": "decision_subject_id",
            "label": "Decision subject ID",
            "role": "evidence",
            "kind": "categorical",
            "value": subject_id,
        },
        {
            "key": "decision_subject_label",
            "label": "Decision subject label",
            "role": "evidence",
            "kind": "categorical",
            "value": subject_label,
        },
        {
            "key": "task_book_url",
            "label": "Book URL",
            "role": "evidence",
            "kind": "textual",
            "value": selected_url,
        },
        {
            "key": "task_book_author",
            "label": "Book author",
            "role": "evidence",
            "kind": "categorical",
            "value": selected_author,
        },
        {
            "key": "task_book_first_published",
            "label": "First published",
            "role": "evidence",
            "kind": "categorical",
            "value": selected_first_published,
        },
    ]
    if basis_secondary is not None:
        decision_facets.append(
            {
                "key": "basis_secondary",
                "label": "Secondary basis",
                "role": "primary",
                "kind": "categorical",
                "value": basis_secondary,
            }
        )

    contexts.extend(
        [
            {
                "key": "decision.primary",
                "label": "Primary decision",
                "contextType": "decision",
                "facets": decision_facets,
            },
            {
                "key": "decision.process",
                "label": "Decision process",
                "contextType": "decision_process",
                "facets": [
                    {
                        "key": "exploration_style",
                        "label": "Exploration style",
                        "role": "primary",
                        "kind": "categorical",
                        "value": exploration_style,
                    },
                    {
                        "key": "options_considered_count",
                        "label": "Options considered count",
                        "role": "score",
                        "kind": "numerical",
                        "value": len(candidates),
                    },
                    {
                        "key": "comparison_notes",
                        "label": "Comparison notes",
                        "role": "explanation",
                        "kind": "textual",
                        "explainsFacetKey": "exploration_style",
                        "value": "Compared: " + "; ".join(
                            candidate["decision_subject_label"] for candidate in candidates
                        ),
                    },
                ],
            },
        ]
    )

    if feedback is not None:
        source_artifacts["userFeedback"] = str(USER_FEEDBACK)
        feedback_facets: list[dict[str, object]] = [
            {
                "key": "overall_experience_rating",
                "label": "Overall experience rating",
                "role": "score",
                "kind": "numerical",
                "value": feedback["overall_experience_rating"],
            },
            {
                "key": "feedback_reason",
                "label": "Feedback reason",
                "role": "explanation",
                "kind": "textual",
                "explainsFacetKey": "overall_experience_rating",
                "value": feedback["feedback_reason"],
            },
            {
                "key": "need_constraint_satisfaction",
                "label": "Need or constraint satisfaction",
                "role": "evidence",
                "kind": "categorical",
                "value": feedback["need_constraint_satisfaction"],
            },
            {
                "key": "personal_preference_satisfaction",
                "label": "Personal preference satisfaction",
                "role": "evidence",
                "kind": "categorical",
                "value": feedback["personal_preference_satisfaction"],
            },
        ]
        for key, label in (
            ("trust_level", "Choice confidence"),
            ("effort_rating", "Effort rating"),
        ):
            if key in feedback:
                feedback_facets.append(
                    {
                        "key": key,
                        "label": label,
                        "role": "score",
                        "kind": "numerical",
                        "value": feedback[key],
                    }
                )
        if "clarity_of_next_step" in feedback:
            feedback_facets.append(
                {
                    "key": "clarity_of_next_step",
                    "label": "Clarity of next step",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": feedback["clarity_of_next_step"],
                }
            )
        contexts.append(
            {
                "key": "user_feedback.primary",
                "label": "User feedback",
                "contextType": "user_feedback",
                "facets": feedback_facets,
            }
        )

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
            "sourceArtifacts": source_artifacts,
            "contexts": contexts,
        }
    )
