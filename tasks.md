# tasks.md — claude-mirror v-next staging

This file is a staging area for ideas and phases that aren't ready for GitHub issues yet. Items graduate to issues once they have:

- Clear scope
- Defined acceptance criteria
- Resolved design questions

For the live, contributor-ready issue list, see the [v-next roadmap tracker](https://github.com/criatvt/claude-mirror/issues/14).

---

## Phase 2 — Loop closure

The quarterly ritual becomes predict-then-verify. Each report ends with 2-3 falsifiable hypotheses about how the user's behaviour will change next quarter. Each new report opens with a verdict on the prior quarter's predictions.

### What needs to be designed

- **Hypothesis emission.** The brief produces a structured `predictions` block at the end. JSON-shaped so it can be parsed and scored.
- **Persistence.** Predictions stored across runs. Three candidate locations:
  - Append to `config.json` under a `predictions[]` key
  - Sibling file `predictions.json`
  - Per-quarter snapshot, e.g., `output/predictions-2026-Q2.json`
- **Verdict template.** Next quarter's report opens with: *"Last quarter you predicted X. Here's the data."*
- **Hypothesis dimensions.** Volume & mix shifts only (per design conversation) — keeps measurement light and doesn't require deep-reading data.

### Open questions

- How does the user *feel* about a prediction the model made on their behalf? Is there an opt-out per prediction?
- First run has no prior predictions to verify — how does the verdict template handle the empty case gracefully?
- How does the verdict handle predictions that are partially correct or missed by a small margin?

### Why not on GitHub yet

- Persistence design unresolved (config.json vs separate file vs snapshots).
- The hypothesis emission prompt structure needs more thinking.
- Scoring edge cases need spec'ing before a contributor could pick it up cleanly.

---

## Phase 3 — Onboarding rewrite

Replace the current `input()`-based form-fill in `onboarding.py` with a TUI library (questionary, prompt_toolkit, etc.). Option-pick for most questions; *"Other (type your own)"* fallback everywhere. Pre-fill from prior `config.json` on re-runs so re-onboarding becomes a quick check-in rather than a fresh form.

### What needs to be designed

- **Library choice.** `questionary`, `prompt_toolkit`, `inquirer`, or `rich.prompt` — each has tradeoffs in look, dependency weight, and Windows support.
- **Question set.** Existing four (after issue #3 cuts mother_tongue) plus *current state and pressures*, plus model selection (depends on #10 plumbing landing first).
- **Pre-fill mechanic.** When `config.json` exists, prior answers shown as default selections. User edits only what changed.
- **Layered onboarding.** Stable identity (set once, rarely changes) vs. quarterly check-in (re-confirm each quarter). Avoid asking the same boring questions every time.

### Open questions

- For *current state and pressures* — what's the curated universe of pressure-type options?
- Should the model-selection question live in onboarding, or in a separate `settings.py` run?
- How does pre-fill behave when the user wants to fully rethink an answer? Need an obvious "start fresh" escape hatch.

### Why not on GitHub yet

- Library choice is unresolved.
- The pressure-type option list needs curation.
- The layered (identity vs. check-in) structure isn't fully designed.

---

## Deferred to v3+

Flagged for the future, not actively planned.

- **One-click installer for non-technical users.** A bundled `.dmg` / `.exe` / `.AppImage` that handles Python + Ollama + Mistral pull, with a GUI launcher. Significant work; held until depth track stabilises. The depth improvements (Phases 0, 1, 4) need to land first so the installer wraps a tool worth shipping to the majority audience.
- **Rename to a platform-agnostic name.** "Claude Mirror" is platform-locked even though the tool already supports ChatGPT and Gemini exports. The rebrand naturally pairs with the installer. Naming directions to consider when ready:
  - **Mirror/reflection family** — *Mirror*, *Reflect*, *Looking Glass*. Continuity with current brand.
  - **Self-knowledge family** — *Aside*, *Lens*, *Hindsight*. Implies depth.
  - **Pattern/trace family** — *Trace*, *Through Line*, *Outline*. Data-grounded.

  Constraints: must fit the existing serif aesthetic (Cormorant Garamond, Prussian blue), one or two words max for domain availability, no vendor names, no startup-tech cuteness.

---

## Open design decisions (cross-phase)

### Single-model vs two-model architecture (referenced in #10, #11)

Should the user pick one local model used for both classification and brief generation, or pick two (small for classify, larger for brief)?

- **Single model** — simpler, less disk, brief quality may suffer when the user picks a small model for RAM reasons.
- **Two models** — more accurate, more cognitive load during onboarding, larger total download.

Decision needed before issue #11 (curated model docs) is finalised. Current lean: single-model for v-next, two-model as a v3+ refinement once the multi-model UX has been observed in real use.
