# IKEA Room Planner (CUA — Docker Linux desktop)

MatrAIx **CUA** (computer-use) web task on a live public retail site: a persona
designs a room with IKEA's Room Planner / Home Design tool. A real **headed
Chromium** window runs in a Docker Linux desktop (Xvfb + XFCE) and
`persona-computer-1` drives it from **screenshots** (navigate / click / scroll /
type via xdotool), finishing with a **done** action after writing
`/app/output/room_plan.json` from the desktop terminal.

- URL: `https://www.ikea.com/us/en/home-design/room/?roomType=generic#1d9a5bb8-08b5-43aa-ab0c-ff91d92c95f9/0943b0b9-198c-4e74-b287-171db3f4ad35`
  (the `#<design-id>/<scene-id>` fragment is **required** — see [Notes](#notes))
- Output: `/app/output/room_plan.json`
- Environment: `application/shared-web-cua-linux`

## Why a CUA variant

IKEA's Room Planner is a heavy 3D/WebGL drag-and-drop canvas behind bot
protection. A headed desktop browser under Xvfb sends a normal Chrome
user-agent natively (clearing UA/automation-fingerprint blocks with no patch)
and the screenshot loop is closer to real end-user behaviour than DOM-only
browsing — the trade-off is that CUA runs are slower and costlier
(screenshot → model → xdotool, many steps). See
[web-interaction.md](../../../docs/guides/web-interaction.md) § CUA for the mode comparison.

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-computer-1` |
| Environment | `docker` (Linux Xvfb, `network_mode = "public"`) |
| Persona | `persona/datasets/matraix-persona-dev-sample/persona_0042.yaml` |
| API key | `ANTHROPIC_API_KEY` (or Bedrock: `AWS_BEARER_TOKEN_BEDROCK` + `AWS_REGION`) |
| `enable_webgl` | `true` — **required**, see [Notes](#notes) |
| `max_turns` | `85` — **required on Bedrock**, see [Notes](#notes) |

Anthropic API:

```bash
uv sync --extra computer-1
export ANTHROPIC_API_KEY=...
uv run harbor run \
  -a persona-computer-1 \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/matraix-persona-dev-sample/persona_0042.yaml \
  -p application/tasks/web_ikea-room-planner
```

Bedrock (this repo's host default — Sonnet 4.5 computer-use over a Bedrock
bearer token):

```bash
export AWS_BEARER_TOKEN_BEDROCK=...   # Bedrock API key
export AWS_REGION=us-east-1
uv run harbor run -c configs/jobs/example-job-recipe/appSim-web_ikea-room-planner-bedrock.yaml
```

Oracle (reference submission; no live desktop):

```bash
uv run harbor run -p application/tasks/web_ikea-room-planner -a oracle
```

## Notes

- The verifier checks the **submission schema** (≥3 products with names/prices,
  ≥1 IKEA series, valid budget/room/fit enums, ≥1 modification, ≥1 safety-
  guidance entry, a professional-boundary field, and a written reason) — not
  semantic match to live inventory, which changes over time. On success it
  emits `structured_output.json` with `task_outcome`, `web_artifact`,
  `decision`, `personalization`, `safety_guidance`, and `user_feedback`
  contexts, which `reporting.json` `contextRules` aggregate into the batch
  metrics: design personalization, budget / lifestyle fit, and safety +
  professional-boundary quality.
- CUA writes `room_plan.json` itself from the desktop terminal before finishing
  with a **done** action (no `cua_submission_profile` is needed for this custom
  schema — the profile materializers only cover the fixed decision schemas).
- **The URL fragment is required.** `?roomType=generic` on its own (no `#`)
  leaves the planner stuck on "Preparing your room ..." indefinitely — verified
  in headed Chromium: still spinning at t+45s, while the fragment URL reaches an
  interactive canvas in ~5s from a cold profile. `/home-design/room/` with no
  query behaves the same way. The fragment names the design/scene to load, so it
  must be kept verbatim wherever this task's URL appears (`instruction.md`,
  `solution/solve.sh`, the Playground registry entry).
- Known limitation: driving IKEA's 3D canvas by screenshot is demanding and
  slow (~20+ min, many steps). The oracle path emits a schema-valid reference
  submission for a completed job + batch report without a live desktop.
- **This task needs `enable_webgl: true`.** IKEA's planner is WebGL2-only
  ("Betrakta Material Shaders are enabled and require WebGL2, which isn't
  supported on this device"). The Computer1 desktop has no GPU and starts
  Chromium with `--disable-gpu` by default, which drops WebGL entirely — so the
  planner loads but never becomes usable, and the agent gives up on the tool.
  Passing `enable_webgl: true` in the agent `kwargs` (see the Bedrock recipe)
  swaps that for ANGLE + SwiftShader software rasterisation, which reports
  `webgl2=true` on the same GPU-less desktop. It is **opt-in per task**: the
  default is unchanged, so no other CUA task is affected. Verified headed under
  Xvfb in `shared-web-cua-linux`:

  | Chromium GL flags | WebGL2 |
  |---|---|
  | `--disable-gpu` (default) | `false` — renderer `none` |
  | `--use-gl=angle --use-angle=swiftshader` | `true` — ANGLE/SwiftShader (Vulkan 1.3) |

  Software rasterisation is slower than no GL at all, which is why it stays
  opt-in rather than becoming the default. It is also CPU-heavy: the container
  sat at ~206% CPU of its 2-core limit for a whole run (memory was fine, ~708
  MiB of 4 GiB), so raising `cpus` in `task.toml` is worth considering if runs
  feel slow.
- **`max_turns: 85` is required on Bedrock — this task will fail without it.**
  Bedrock refuses any request carrying more than 100 images:

  ```
  Error code: 400 - {'message': 'Too much media: 0 document pages + 101 images > 100'}
  ```

  Each CUA step adds one screenshot, so a long run walks straight into that
  ceiling. The runtime *can* trim screenshot history
  (`Computer1Compactor._trim_old_screenshots`, keeps the last 3), but only during
  **token**-triggered compaction — and tokens are not the binding constraint
  here. Observed across two live runs:

  | Run | Steps | Screenshots | Peak prompt tokens | Compactions | Outcome |
  |---|---|---|---|---|---|
  | verified good | 86 | 84 | 128,528 | 0 | reward 1.0 |
  | uncapped | 99 | 98 | 146,530 | 0 | Bedrock 400 at image 101 |

  Peak tokens stayed ~53k below Sonnet's 200k window, so compaction never fired
  and nothing pruned images. Note the good run cleared the cap by only 16
  screenshots — it was *under* the ceiling, not safely under it. The uncapped run
  spent all 99 steps exploring and never wrote `room_plan.json` at all, so the
  cap is paired with an explicit "have a plan saved by ~turn 70" budget in
  `instruction.md`; a cap alone would just stop a run that had not submitted yet.

  This is a shared-runtime gap (any long CUA run on Bedrock can hit it), not
  something specific to IKEA — the per-task cap is the contained workaround. A
  general fix would be an image-count trigger for compaction alongside the token
  one, which is deliberately **not** part of this PR.
