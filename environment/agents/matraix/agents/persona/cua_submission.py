"""Materialize CUA trajectory submissions onto the task environment filesystem."""

from __future__ import annotations

import json
import re
import shlex
from collections.abc import Callable
from pathlib import Path
from typing import Any

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)

TERMINAL_COMPUTER_ACTION_TYPES = frozenset({"done", "answer", "terminate"})

BOOK_INTEREST_REQUIRED_KEYS = frozenset({"title", "price_gbp", "interested", "reason"})
ECOMMERCE_INTERACTION_REQUIRED_KEYS = frozenset(
    {
        "selected_product_id",
        "selected_product_name",
        "need_satisfaction",
        "ease_of_use",
        "overall_experience_rating",
        "reason",
    }
)
IOS_DECISION_REQUIRED_KEYS = frozenset(
    {"keep_notifications_on", "app_reviewed", "reason"}
)
IOS_NEWS_SUBSCRIPTION_REQUIRED_KEYS = frozenset(
    {"app_reviewed", "clicked_get_started", "price_seen", "highlights_noticed", "reason"}
)


def _first_balanced_json_object(text: str) -> str | None:
    """Return the first top-level ``{...}`` span, respecting strings/escapes."""
    if not text:
        return None
    start = -1
    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(text):
        if escape:
            escape = False
            continue
        if in_string:
            if char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth == 0:
                continue
            depth -= 1
            if depth == 0 and start != -1:
                return text[start : index + 1]
    return None


def parse_json_payload(raw: str) -> dict[str, Any] | None:
    """Parse a JSON object from plain text or a fenced code block.

    Prefer a fenced block when present. Otherwise take the first balanced
    ``{...}`` so trailing commentary / a second JSON block does not poison
    ``json.loads`` (common on computer-use final answers).
    """
    text = raw.strip()
    if not text:
        return None
    fence = _JSON_FENCE_RE.search(text)
    candidates: list[str] = []
    if fence:
        candidates.append(fence.group(1).strip())
    candidates.append(text)
    balanced = _first_balanced_json_object(text)
    if balanced is not None:
        candidates.append(balanced)

    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


def _has_required_keys(data: dict[str, Any], required: frozenset[str]) -> bool:
    return required <= data.keys()


def _payload_from_computer_action(arguments: dict[str, Any]) -> dict[str, Any] | None:
    action_type = arguments.get("type")
    if action_type not in TERMINAL_COMPUTER_ACTION_TYPES:
        return None
    for field in ("result", "text"):
        value = arguments.get(field)
        if isinstance(value, str):
            parsed = parse_json_payload(value)
            if parsed is not None:
                return parsed
    return None


def _extract_payload_from_trajectory(
    trajectory: dict[str, Any],
    *,
    required_keys: frozenset[str],
    accept_payload: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any] | None:
    steps = trajectory.get("steps")
    if not isinstance(steps, list):
        return None

    def _accept(data: dict[str, Any] | None) -> dict[str, Any] | None:
        if data is None or not _has_required_keys(data, required_keys):
            return None
        if accept_payload is not None and not accept_payload(data):
            return None
        return data

    for step in reversed(steps):
        if step.get("source") != "agent":
            continue

        tool_calls = step.get("tool_calls") or []
        for call in reversed(tool_calls):
            function_name = call.get("function_name")
            arguments = call.get("arguments") or {}

            if function_name == "done":
                message = arguments.get("message")
                if isinstance(message, str):
                    accepted = _accept(parse_json_payload(message))
                    if accepted is not None:
                        return accepted

            if function_name == "mark_task_complete":
                result = arguments.get("result")
                if isinstance(result, str):
                    accepted = _accept(parse_json_payload(result))
                    if accepted is not None:
                        return accepted

            if function_name == "computer_action":
                accepted = _accept(_payload_from_computer_action(arguments))
                if accepted is not None:
                    return accepted

        message = step.get("message")
        if isinstance(message, str):
            accepted = _accept(parse_json_payload(message))
            if accepted is not None:
                return accepted

    return None


def extract_ios_decision_from_trajectory(
    trajectory: dict[str, Any],
) -> dict[str, Any] | None:
    """Return the last valid iOS notification decision object from a trajectory."""

    def _validate(data: dict[str, Any]) -> bool:
        return isinstance(data.get("keep_notifications_on"), bool)

    return _extract_payload_from_trajectory(
        trajectory,
        required_keys=IOS_DECISION_REQUIRED_KEYS,
        accept_payload=_validate,
    )


def extract_ios_news_subscription_from_trajectory(
    trajectory: dict[str, Any],
) -> dict[str, Any] | None:
    """Return the last valid iOS News+ subscription decision from a trajectory."""

    def _validate(data: dict[str, Any]) -> bool:
        if not isinstance(data.get("clicked_get_started"), bool):
            return False
        highlights = data.get("highlights_noticed")
        if not isinstance(highlights, list) or not highlights:
            return False
        reason = data.get("reason")
        return isinstance(reason, str) and len(reason.strip()) >= 10

    return _extract_payload_from_trajectory(
        trajectory,
        required_keys=IOS_NEWS_SUBSCRIPTION_REQUIRED_KEYS,
        accept_payload=_validate,
    )


def extract_book_interest_from_trajectory(
    trajectory: dict[str, Any],
) -> dict[str, Any] | None:
    """Return the last valid book-interest payload from a Docker CUA trajectory."""

    def _validate(data: dict[str, Any]) -> bool:
        return isinstance(data.get("interested"), bool)

    return _extract_payload_from_trajectory(
        trajectory,
        required_keys=BOOK_INTEREST_REQUIRED_KEYS,
        accept_payload=_validate,
    )


def _valid_ecommerce_score(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 10


def extract_ecommerce_interaction_from_trajectory(
    trajectory: dict[str, Any],
) -> dict[str, Any] | None:
    """Return the last valid ecommerce web submission from an OpenHands trajectory."""

    def _validate(data: dict[str, Any]) -> bool:
        for field in (
            "need_satisfaction",
            "ease_of_use",
            "overall_experience_rating",
        ):
            if not _valid_ecommerce_score(data.get(field)):
                return False
        reason = data.get("reason")
        return isinstance(reason, str) and len(reason.strip()) >= 20

    return _extract_payload_from_trajectory(
        trajectory,
        required_keys=ECOMMERCE_INTERACTION_REQUIRED_KEYS,
        accept_payload=_validate,
    )


async def materialize_json_file(
    environment: Any,
    logs_dir: Path,
    *,
    extractor: Callable[[dict[str, Any]], dict[str, Any] | None],
    output_path: str,
    logger: Any | None = None,
    log_label: str = "cua submission",
) -> bool:
    """Write *output_path* in the environment from trajectory JSON."""
    trajectory_path = logs_dir / "trajectory.json"
    if not trajectory_path.is_file():
        return False

    try:
        trajectory = json.loads(trajectory_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        if logger:
            logger.warning("%s: could not read trajectory: %s", log_label, exc)
        return False

    payload_obj = extractor(trajectory)
    if payload_obj is None:
        if logger:
            logger.warning(
                "%s: no valid JSON submission in trajectory; "
                "agent should finish with a done/answer action",
                log_label,
            )
        return False

    payload = json.dumps(payload_obj, ensure_ascii=False)
    parent = str(Path(output_path).parent)
    command = (
        f"mkdir -p {shlex.quote(parent)} && "
        f"cat > {shlex.quote(output_path)} <<'EOF'\n{payload}\nEOF"
    )
    result = await environment.exec(command, timeout_sec=30)
    if result.return_code != 0:
        if logger:
            logger.warning(
                "%s: host write failed rc=%s stderr=%s",
                log_label,
                result.return_code,
                (result.stderr or "")[:200],
            )
        return False

    if logger:
        logger.info("%s: wrote %s from trajectory submission", log_label, output_path)
    return True


async def materialize_book_interest_file(
    environment: Any,
    logs_dir: Path,
    *,
    output_path: str = "/app/output/book_interest.json",
    logger: Any | None = None,
) -> bool:
    """Write book_interest.json from a Docker Linux CUA done/answer submission."""
    return await materialize_json_file(
        environment,
        logs_dir,
        extractor=extract_book_interest_from_trajectory,
        output_path=output_path,
        logger=logger,
        log_label="linux web submission",
    )


async def materialize_ecommerce_interaction_file(
    environment: Any,
    logs_dir: Path,
    *,
    output_path: str = "/app/output/ecommerce_interaction.json",
    logger: Any | None = None,
) -> bool:
    """Write ecommerce_interaction.json from an OpenHands web-task final answer."""
    return await materialize_json_file(
        environment,
        logs_dir,
        extractor=extract_ecommerce_interaction_from_trajectory,
        output_path=output_path,
        logger=logger,
        log_label="ecommerce web submission",
    )


async def materialize_ios_news_subscription_file(
    environment: Any,
    logs_dir: Path,
    *,
    output_path: str = "/app/output/decision.json",
    logger: Any | None = None,
) -> bool:
    """Write decision.json from an iOS News+ subscription CUA trajectory."""
    return await materialize_json_file(
        environment,
        logs_dir,
        extractor=extract_ios_news_subscription_from_trajectory,
        output_path=output_path,
        logger=logger,
        log_label="ios news subscription",
    )


def extract_final_answer_text(trajectory: dict[str, Any]) -> str:
    """Return the last non-empty agent message — task-agnostic hand-in text."""
    steps = trajectory.get("steps")
    if not isinstance(steps, list):
        return ""
    for step in reversed(steps):
        if not isinstance(step, dict):
            continue
        if step.get("source") != "agent":
            continue
        # Prefer terminal tool payloads when present (done/answer/mark_task_complete).
        tool_calls = step.get("tool_calls") or []
        if isinstance(tool_calls, list):
            for call in reversed(tool_calls):
                if not isinstance(call, dict):
                    continue
                arguments = call.get("arguments") or {}
                if not isinstance(arguments, dict):
                    continue
                name = call.get("function_name")
                if name == "done" and isinstance(arguments.get("message"), str):
                    text = arguments["message"].strip()
                    if text:
                        return text
                if name == "mark_task_complete" and isinstance(
                    arguments.get("result"), str
                ):
                    text = arguments["result"].strip()
                    if text:
                        return text
                if name == "computer_action":
                    action_type = arguments.get("type")
                    if action_type in TERMINAL_COMPUTER_ACTION_TYPES:
                        for field in ("result", "text"):
                            value = arguments.get(field)
                            if isinstance(value, str) and value.strip():
                                return value.strip()
        message = step.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    return ""


async def materialize_final_answer_file(
    environment: Any,
    logs_dir: Path,
    *,
    logger: Any | None = None,
    output_paths: tuple[str, ...] = (
        "/app/output/final_answer.txt",
        "/logs/agent/final_answer.txt",
    ),
) -> bool:
    """Persist the agent's final answer text — no task-specific schema.

    Writes host ``logs_dir/final_answer.txt`` and mirrors into the environment
    under ``/app/output`` (artifact collection) plus the agent logs path that
    verifiers already probe. Task ``test.sh`` / host_verifier turn this into
    the task's named JSON artifact.
    """
    trajectory_path = logs_dir / "trajectory.json"
    if not trajectory_path.is_file():
        return False
    try:
        trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        if logger:
            logger.warning("final_answer: could not read trajectory: %s", exc)
        return False
    if not isinstance(trajectory, dict):
        return False

    text = extract_final_answer_text(trajectory)
    if not text:
        if logger:
            logger.warning("final_answer: no agent message found in trajectory")
        return False

    host_target = logs_dir / "final_answer.txt"
    try:
        host_target.write_text(text, encoding="utf-8")
    except OSError as exc:
        if logger:
            logger.warning("final_answer: host write failed: %s", exc)
        return False

    wrote_env = False
    for output_path in output_paths:
        parent = str(Path(output_path).parent)
        command = (
            f"mkdir -p {shlex.quote(parent)} && "
            f"cat > {shlex.quote(output_path)} <<'MATRAIX_FINAL_ANSWER_EOF'\n"
            f"{text}\n"
            "MATRAIX_FINAL_ANSWER_EOF"
        )
        try:
            result = await environment.exec(command, timeout_sec=30)
        except Exception as exc:  # noqa: BLE001
            if logger:
                logger.warning(
                    "final_answer: env write %s failed: %s", output_path, exc
                )
            continue
        if getattr(result, "return_code", 1) != 0:
            if logger:
                logger.warning(
                    "final_answer: env write %s rc=%s stderr=%s",
                    output_path,
                    getattr(result, "return_code", None),
                    (getattr(result, "stderr", None) or "")[:200],
                )
            continue
        wrote_env = True

    if logger:
        logger.info(
            "final_answer: wrote host %s%s",
            host_target,
            " and environment mirrors" if wrote_env else " (env mirror skipped)",
        )
    return True


_SUBMISSION_PROFILES: dict[str, Callable[..., Any]] = {
    "book_interest": materialize_book_interest_file,
    "ecommerce_interaction": materialize_ecommerce_interaction_file,
    "ios_news_subscription": materialize_ios_news_subscription_file,
}


async def materialize_cua_submission_profile(
    profile: str,
    environment: Any,
    logs_dir: Path,
    *,
    logger: Any | None = None,
) -> bool:
    """Run a named post-run submission materializer."""
    normalized = profile.strip().lower().replace("-", "_")
    handler = _SUBMISSION_PROFILES.get(normalized)
    if handler is None:
        if logger:
            logger.warning("unknown cua_submission_profile=%r", profile)
        return False
    return await handler(environment, logs_dir, logger=logger)
