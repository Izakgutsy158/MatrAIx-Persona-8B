# Choose your next book on Open Library

## Your situation

You are choosing one book to read next. Read the scenario brief in
`input/context.md`, then use the live Open Library website to make the choice.

## Your goal

Search or browse the public catalog, open and inspect at least **three distinct
book detail pages** (work pages), compare the books, and choose the one you
would most want to read next.

## Constraints on your behavior

- Use only information visible on the live Open Library site. Do not invent
  titles, authors, publication dates, subjects, or descriptions.
- Choose as yourself: your interests, reading habits, available time, and life
  situation decide what fits — not what sounds most prestigious.
- Do not log in, borrow, download, donate, purchase, share, contact anyone, or
  visit a third-party site.

## Interaction requirements

Use the live website in the browser. Compare book descriptions, subjects,
authors, and publication information when they are relevant to you. Save your
choice to `/app/output/book_choice.json`:

```json
{
  "decision_subject_id": "<Open Library work ID from the selected URL, e.g. OL45804W>",
  "decision_subject_label": "<book title copied from the main heading of its work page>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "basis_secondary": "<optional second value from the same enumeration>",
  "exploration_style": "<compared_multiple|deep_research>",
  "reason": "<why this book fits your interests, reading habits, and situation, grounded in the pages you inspected>",
  "task_book_url": "https://openlibrary.org/works/<work-id>/<title-slug>",
  "task_book_author": "<author name exactly as shown on the work page>",
  "task_book_first_published": "<first publication year exactly as shown>",
  "task_options_considered": [
    {
      "decision_subject_id": "<work ID>",
      "decision_subject_label": "<book title copied from the main heading of its work page>",
      "task_book_url": "https://openlibrary.org/works/<work-id>/<title-slug>",
      "task_book_author": "<author name exactly as shown>",
      "task_book_first_published": "<first publication year exactly as shown>",
      "task_relevance_note": "<why this was a plausible candidate for you>"
    }
  ]
}
```

## Termination criteria

- `task_options_considered` must contain at least three distinct books whose
  work pages you actually opened.
- For every book you record, copy its title from the main heading of that
  book's work page, not from a search result, list card, browser title, or
  snippet.
- The selected book must appear in `task_options_considered`, with matching
  title, work ID, URL, author, and first-published year.
- Use the Open Library work ID from the URL (the `OL...W` part) as
  `decision_subject_id`.
- Keep titles, authors, and years faithful to the live pages; do not invent
  metadata.
- `basis_secondary` is optional. If included, it must differ from
  `basis_primary`.
- Because comparison is required, use `compared_multiple` or `deep_research`
  for `exploration_style`.
- Keep `reason` specific to what matters to you and evidence from the selected
  book's page.
- Finish after saving the completed JSON file.

## Success judgment

The task is successful when the saved JSON follows the required structure, the
candidate list contains at least three work pages you visited, the selected
book matches one candidate, and all recorded titles, work IDs, URLs, authors,
and years are faithful to the live site.
