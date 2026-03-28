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
analyse.py      → reads config + data/, prints stats
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

Gen Z aesthetic, light mode:
- Background: `#FFFFFF`
- Text: `#0D0D0D`
- Primary accent: `#7C3AED` (violet)
- Secondary accents: `#FF4D6D`, `#00C896`, `#FFD600`, `#0EA5E9`
- Font: Inter (data/body), Space Grotesk (headings/numbers)
- Charts: white background, saturated palette, clean gridlines

Do NOT change the aesthetic to corporate/muted/conservative.

---

## Do Not

- Do not add external API calls without explicit user consent
- Do not store API keys
- Do not split the report into multiple HTML files
- Do not add V2 features (browser UI, GapFinder integration) without a separate branch
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
