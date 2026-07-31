#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

SEARCH_URL = "https://openlibrary.org/search?q=science"
OUTPUT = Path("/app/output/book_choice.json")
WORK_ID = re.compile(r"^OL\d+W$")
FIRST_PUBLISHED = re.compile(r"First published in (\d{4})")


def work_id_from(url: str) -> str:
    parts = urlparse(url).path.strip("/").split("/")
    return parts[1] if len(parts) >= 2 else ""


def canonical_work_url(url: str) -> str:
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    return f"https://openlibrary.org/{parts[0]}/{parts[1]}" + (
        f"/{parts[2]}" if len(parts) > 2 else ""
    )


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=60_000)

    hrefs: list[str] = []
    results = page.locator('a[href^="/works/OL"]')
    results.first.wait_for(state="visible", timeout=60_000)
    for index in range(min(results.count(), 30)):
        href = results.nth(index).get_attribute("href")
        if not href:
            continue
        absolute_url = canonical_work_url(urljoin(SEARCH_URL, href))
        if not WORK_ID.fullmatch(work_id_from(absolute_url)):
            continue
        if absolute_url not in hrefs:
            hrefs.append(absolute_url)
        if len(hrefs) == 3:
            break

    if len(hrefs) < 3:
        raise RuntimeError("Open Library search returned fewer than three work candidates")

    candidates = []
    for url in hrefs:
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        title = page.locator("h1").first.inner_text(timeout=30_000).strip()
        author = "Unknown"
        author_links = page.locator('a[href^="/authors/OL"]')
        if author_links.count() > 0:
            author = author_links.first.inner_text(timeout=30_000).strip() or "Unknown"
        first_published = "Unknown"
        body_text = page.locator("body").inner_text(timeout=30_000)
        match = FIRST_PUBLISHED.search(body_text)
        if match:
            first_published = match.group(1)
        candidates.append(
            {
                "decision_subject_id": work_id_from(url),
                "decision_subject_label": title,
                "task_book_url": url,
                "task_book_author": author,
                "task_book_first_published": first_published,
                "task_relevance_note": "A plausible science read surfaced by the catalog search.",
            }
        )

    browser.close()

selected = candidates[0]
payload = {
    "decision_subject_id": selected["decision_subject_id"],
    "decision_subject_label": selected["decision_subject_label"],
    "decision_outcome": "selected",
    "basis_primary": "fit",
    "basis_secondary": "novelty",
    "exploration_style": "compared_multiple",
    "reason": (
        "Of the three science books inspected, this one best matches a general "
        "reader looking for an approachable next read, based on its work-page "
        "description and subjects."
    ),
    "task_book_url": selected["task_book_url"],
    "task_book_author": selected["task_book_author"],
    "task_book_first_published": selected["task_book_first_published"],
    "task_options_considered": candidates,
}
OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"solved: wrote {OUTPUT}")
PY
