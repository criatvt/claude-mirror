# claude-mirror

**Hold up a mirror to how you use AI.**

claude-mirror reads your exported AI conversation history, classifies every conversation, and generates a single beautiful report — charts, patterns, and a personalised coaching brief — all running locally on your machine.

> Built by [Aasif Iqbal J.](https://aasifj.com) with Claude.

---

## What You Get

One scrollable HTML report containing:

- **Monthly volume** — how your usage has grown over time
- **Topic mix** — what you use AI for most (Writing, Research, Coding, Strategy, etc.)
- **Activity heatmap** — when you work (day × hour)
- **Conversation depth** — how deep your sessions go
- **Category trends** — how your usage has shifted over time
- **Word cloud** — what topics dominate your conversations
- **The Mirror** — a thoughtful read of your data, generated locally: the story so far, what stood out, what's missing, what's worth trying

Plus a `report.md` — the same content in Markdown, designed to be reused, versioned, and pasted into future AI conversations.

---

## Supported Platforms

| Platform | Export location |
|----------|----------------|
| **Claude** | claude.ai → Settings → Account → Export data |
| **ChatGPT** | chat.openai.com → Settings → Data controls → Export data |
| **Gemini** | myaccount.google.com → Data & Privacy → Export or download your data |

Export arrives as a zip file via email. Unzip it — you'll find a `conversations.json` inside.

---

## Privacy

**Everything runs on your machine. Nothing leaves it.**

- Uses [Ollama](https://ollama.com) to run Mistral 7B locally for classification and brief generation
- No API calls to external servers
- No accounts, no sign-up, no telemetry, no tracking
- Your `conversations.json` never leaves your computer

---

## Requirements

- Python 3.9 or higher
- [Ollama](https://ollama.com) installed
- Mistral model: `ollama pull mistral`
- macOS, Linux, or Windows (WSL recommended on Windows)

Check your Python version:
```bash
python3 --version
```

---

## Installation

### Step 1 — Clone the repo
```bash
git clone https://github.com/criatvt/claude-mirror
cd claude-mirror
```

### Step 2 — Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```
On Windows:
```bash
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Install Ollama

Ollama is the local model runtime — it's what keeps everything offline.

**macOS:**
```bash
brew install ollama
```
Or download the `.dmg` from [ollama.com/download](https://ollama.com/download).

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download the installer from [ollama.com/download](https://ollama.com/download).

After installing, start the Ollama service (it usually starts automatically; if not):
```bash
ollama serve
```
Leave it running in a separate terminal window for the rest of the setup.

Verify it's reachable:
```bash
curl http://localhost:11434/api/tags
```
You should get a JSON response (an empty model list is fine — that means it's running).

### Step 5 — Pull the Mistral model
```bash
ollama pull mistral
```
This downloads ~4GB. Takes a few minutes depending on your connection. One-time only.

---

## Usage

### Step 1 — Place your export in the data folder

Create a `data/` folder inside `claude-mirror/`:
```bash
mkdir data
```

Copy your `conversations.json` into it:
```
claude-mirror/
└── data/
    └── conversations.json
```

> **Note:** Only `conversations.json` is needed. You can ignore other files in the export.

### Step 2 — Run onboarding (one-time)
```bash
python3 onboarding.py
```

This asks you 4 quick questions:
1. Your name
2. Your profession (max 60 characters)
3. Your current top goal (max 100 characters)
4. Time period to analyse (3 months / 6 months / 12 months / all data)

Takes under 2 minutes. Saves to `config.json` locally.

### Step 3 — Classify conversations
```bash
python3 classify.py
```

Sends each conversation to Mistral (running locally) for classification.
- **Time:** roughly 1–3 seconds per conversation. A few hundred conversations classify in a few minutes.
- **Progress:** Live progress bar
- **Resumable:** If interrupted, run again — it picks up where it left off
- **Output:** `classified.csv`

### Step 4 — Generate your report
```bash
python3 report.py
```

Generates all charts and your personal brief.
- **Time:** under a minute for the charts, plus ~30 seconds for the brief
- **Output:** `output/report.html` and `output/report.md`

### Step 5 — Open your report
```bash
open output/report.html
```

On Linux:
```bash
xdg-open output/report.html
```

On Windows:
```bash
start output/report.html
```

---

## Every Time You Re-Run

To update your report with fresh data:

1. Export new data from your AI platform
2. Replace `data/conversations.json` with the new file
3. Delete `classified.csv` (to reclassify everything) or keep it (to only classify new conversations)
4. Run `python3 classify.py`
5. Run `python3 report.py`
6. Open `output/report.html`

> **Tip:** Run monthly. The most interesting insights come from watching how your usage evolves over time.

---

## File Structure

```
claude-mirror/
├── data/
│   └── conversations.json     ← Place your export here
├── output/
│   ├── report.html            ← Your report (open in browser)
│   └── report.md              ← Your report (Markdown, reusable)
├── venv/                      ← Python virtual environment
├── onboarding.py              ← Step 1: setup
├── classify.py                ← Step 2: classify conversations
├── report.py                  ← Step 3: generate report
├── config.json                ← Your saved onboarding answers
├── classified.csv             ← Classification results
├── requirements.txt
├── README.md
└── CLAUDE.md
```

---

## Troubleshooting

**`(venv)` not showing in terminal**
Run `source venv/bin/activate` (Mac/Linux) or `venv\Scripts\activate` (Windows) before any script.

**Ollama not running**
Run `ollama serve` in a separate terminal window, then retry.

**classify.py interrupted**
Just run it again. It resumes automatically from where it stopped.

**Report feels generic**
Re-run `onboarding.py` with more specific answers for your profession and goal, then re-run `report.py`.

**Platform not detected correctly**
Open `data/conversations.json` and check the top-level structure. Claude exports have `chat_messages`, ChatGPT exports have `mapping`. File an issue if your format isn't supported.

**Charts not rendering**
Make sure `output/` folder exists: `mkdir -p output`

---

## Reusing report.md

The Markdown report is designed to be reused:

- **Version it:** Save as `report-2026-Q1.md`, `report-2026-Q2.md` to track change over time
- **Paste into Claude:** "Here is my AI usage report from last quarter. Help me build a learning plan based on my blind spots."
- **Build on it:** Feed it into GapFinder (coming soon) for a personal learning curriculum

---

## Recommended Cadence

| Frequency | Action |
|-----------|--------|
| Monthly | Export fresh data, re-run classify + report |
| Quarterly | Compare this month's report.md to last quarter's |
| Annually | Re-run onboarding if your profession or goals have changed |

---

## Contributing

Contributions welcome. If you're adding support for a new AI platform:

1. Add detection logic in `classify.py` (the `detect_platform` function)
2. Add message extraction logic for that platform
3. Test with a sample export
4. Submit a PR with a note on how user messages are identified in that platform's JSON

---

## Roadmap

**Today**
- Claude, ChatGPT, Gemini support
- 8 charts + The Mirror (personal reflection)
- Single HTML report
- Fully local — no cloud calls, no telemetry

**In flight** *(see [issue #14](https://github.com/criatvt/claude-mirror/issues/14) for the live tracker)*
- Tighter brief — verbosity caps, two-layer structure, real conversation citations
- Deeper classification — full-conversation reading, per-conversation summaries
- Quarter-on-quarter comparison as a "predictive personal-tracking ritual"
- Configurable local model (drop-in replacement for Mistral)

The project stays terminal-driven and single-HTML-report by design — privacy and screenshot-shareability are non-negotiable.

---

## Credits

Built by/with Claude by [Aasif Iqbal J.](https://aasifj.com) 


---

*Everything runs locally. No data leaves your machine.*
*Your conversations are yours. Your patterns are yours. Your report is yours.*
