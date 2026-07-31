# Open Library Book Choice

MatrAIx web application task on the live public
[Open Library](https://openlibrary.org/) catalog. The persona agent acts as a
reader choosing their next book: it browses or searches the catalog, inspects
at least three distinct work pages, and commits to one choice with a structured
output and a persona-grounded reason.

Claimed in the Application Scenarios doc (Scenario 45) as part of the
web-task scaling effort; follows the `web_mit-ocw-course-choice` pattern.

## What it measures

Book choice is persona-sensitive along axes the persona pool already encodes:
`highest_education` and `cog_reading_vs_watching` (stratified), plus age and
interests through the persona profile. The same open catalog should yield
visibly different selections across segments.

- **Decision** — selected work, primary/secondary basis, persona-grounded
  reason (`decision` context; selected-book and basis distributions).
- **Process** — compare-then-commit with ≥3 distinct work pages
  (`decision_process` context, `options_considered_count`).
- **Fidelity** — titles, authors, work IDs, URLs, and first-published years
  must match the live work pages (verifier-checked structure and
  cross-consistency).
- **Experience** — post-run self-report (satisfaction, confidence, effort).

## Output artifact

`/app/output/book_choice.json` — schema in `instruction.md`. Work IDs use the
Open Library `OL…W` form taken from the work-page URL.

## Environment

```toml
[environment]
definition = "application/shared-web-playwright"
network_mode = "public"
```

Live public site; no login, no API key, no sidecar.
