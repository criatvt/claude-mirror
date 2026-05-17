# CLAUDE.md — claude-mirror
*Instructions for contributors and Claude Code*

---

## What This Is

claude-mirror is a privacy-first, platform-agnostic AI conversation analyser.
It reads a user's exported conversation history, classifies every conversation locally,
and generates a single HTML report with charts and a personalised coaching brief.

Full context in README.md.

---

## Core Principles — Never Violate These

1. **Local only by default** — No data leaves the user's machine. Ollama runs everything locally.
2. **Platform agnostic** — Detect platform from JSON structure. Never assume Claude.
3. **Single output file** — One `report.html`, one `report.md`. No multiple files to open.
4. **No hardcoded personal context** — Everything comes from `config.json` (onboarding answers).

---

## Architecture
```
onboarding.py   → config.json
classify.py     → reads config + data/, writes classified.csv
report.py       → reads config + classified.csv, writes output/report.html + output/report.md
```

---

## Platform Detection

In `classify.py`, detect platform from JSON structure:

| Platform | Key signal |
|----------|-----------|
| Claude | `chat_messages` array with `sender: "human"` |
| ChatGPT | `mapping` object with `author.role: "user"` |
| Gemini | Google Takeout format |

Always normalise to user-messages-only before analysis.

---

## Styling

New Yorker / editorial serif aesthetic, light mode, typography-led:
- Background: `#FBFAF6` (warm white — fresh paper)
- Body text (ink): `#1E1A14` (warm-black)
- Chart anchor: `#3D2E20` (deep walnut — used in charts in place of pure black)
- Accent: `#B85A3D` (terracotta — hero rule, italic wordmark, stat numbers, brief left-border)
- Muted: `#6B5D4A` (captions, eyebrows, footer)
- Hairline: `#E5DFD0` (card borders, dividers)
- Chart palette: 8-tone watercolour-muted earthtones in `report.py:46-55` (walnut, terracotta, sage, ochre, plum, teal, rust, moss)
- Font: Cormorant Garamond (Google Fonts, falls back to Georgia offline) — both headings and body
- Hero: typography-led, NOT a colour block — light page, dark serif title, italic terracotta wordmark
- Cards: white paper, square corners, hairline border, lots of whitespace
- Brief ("The Mirror"): white card with terracotta left-border, drop cap on first paragraph

Do NOT change the aesthetic to Gen Z, high-contrast neon, or corporate flat design.
The terracotta accent should appear *sparingly* — it carries the visual hierarchy, not the whole palette. Charts never use pure black (`#000`); use the walnut `#3D2E20` as the deepest tone.

---

## Do Not

- Do not add external API calls without explicit user consent
- Do not store API keys
- Do not split the report into multiple HTML files
- Do not add V2 features (browser UI) without a separate branch
- Do not change the single-file report structure

---

## Adding Platform Support

1. Add detection in `detect_platform()` in `classify.py`
2. Add extraction in `get_messages()` and `get_text()`
3. Add metadata extraction in `get_conv_meta()`
4. Test with a sample anonymised export
5. Update README supported platforms table

---

*Read README.md for full product context.*
