# Bookshop choice (Docker Linux CUA)

Docker **web** CUA task for a persona-sensitive book decision. The agent browses
the public catalog in a local Linux Xvfb container and submits a structured
choice with a final **done** action.

- URL: https://books.toscrape.com/
- Output: `/app/output/book_interest.json` (recovered by the task verifier from
  the agent's final answer / trajectory when needed)

```bash
uv sync --extra computer-1
export ANTHROPIC_API_KEY=...
uv run harbor run \
  -a persona-computer-1 \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/matraix-persona-dev-sample/persona_0042.yaml \
  -p application/tasks/example-web-cua_bookshop-choice
```

The agent mirrors a task-agnostic `final_answer.txt` into `/app/output`. Task
`tests/test_state.py` recovers `book_interest.json` from that signal (or from
trajectory) and validates the decision schema — no per-task agent submission
profile is required.

The Docker image includes **xfce4-terminal** (`Ctrl+Alt+T`) for optional shell
use, but agents should not rely on manual file saving.

## Example family

| Task | Environment |
|------|-------------|
| **this task** | Docker Linux Xvfb (CUA + task-local recovery) |
| `example-web-playwright_quote-choice` | Quote choice on `quotes.toscrape.com` |
| `example-web-browser-use_laptop-choice` | Laptop shortlist on `webscraper.io` |
| `example-web-cocoa_plan-choice` | Pricing-plan choice on PythonAnywhere |

OS settings tasks live under `application/tasks/example-computer-use-*`, not here.
