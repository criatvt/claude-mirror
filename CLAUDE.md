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

Professional serif aesthetic, light mode:
- Background: `#F5F0E8` (warm off-white)
- Text: `#1B2A3B` (dark navy)
- Primary accent: `#003153` (Prussian Blue)
- Chart palette: Prussian Blue gradient, muted and desaturated
- Font: Cormorant Garamond (headings), serif body
- Charts: warm off-white background, clean gridlines, no saturated colours

Do NOT change the aesthetic to Gen Z, high-contrast neon, or corporate flat design.

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
