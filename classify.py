import json
import os
import pandas as pd
import ollama
from tqdm import tqdm

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, 'config.json')
DATA_PATH = os.path.join(BASE, 'data', 'conversations.json')
SAVE_PATH = os.path.join(BASE, 'classified.csv')

CSV_COLUMNS = [
    'uuid', 'name', 'created_at', 'updated_at', 'message_count',
    'layer1', 'layer2', 'confidence', 'summary', 'key_themes',
]

CONTEXT_BUDGET = 10000
SAMPLE_N = 10

# ── Load config ───────────────────────────────────────────────────────────────
if not os.path.exists(CONFIG_PATH):
    print("Run onboarding first: python3 onboarding.py")
    exit()

with open(CONFIG_PATH) as f:
    config = json.load(f)

with open(DATA_PATH) as f:
    conversations = json.load(f)

platform = config.get('platform', 'claude')
cutoff = config.get('cutoff_date')

# ── Resume support ────────────────────────────────────────────────────────────
if os.path.exists(SAVE_PATH):
    existing = pd.read_csv(SAVE_PATH)
    # Backward compat: ensure new columns exist on older CSVs
    for col in ('summary', 'key_themes'):
        if col not in existing.columns:
            existing[col] = ''
    done_uuids = set(existing['uuid'].tolist())
    print(f"Resuming — {len(done_uuids)} done, {len(conversations) - len(done_uuids)} remaining.")
else:
    existing = pd.DataFrame(columns=CSV_COLUMNS)
    done_uuids = set()
    print(f"Starting fresh — {len(conversations)} conversations to classify.")

# ── Platform-aware extraction ─────────────────────────────────────────────────
def get_messages(conv, platform):
    if platform == 'claude':
        msgs = conv.get('chat_messages', [])
        return [m for m in msgs if m.get('sender') == 'human' and m.get('text', '').strip()]
    elif platform == 'chatgpt':
        mapping = conv.get('mapping', {})
        return [
            v for v in mapping.values()
            if v.get('message') and
            v['message'].get('author', {}).get('role') == 'user' and
            v['message'].get('content', {}).get('parts')
        ]
    return []

def get_text(msg, platform):
    if platform == 'claude':
        return msg.get('text', '')
    elif platform == 'chatgpt':
        parts = msg.get('message', {}).get('content', {}).get('parts', [])
        return ' '.join([p for p in parts if isinstance(p, str)])
    return ''

def get_conv_meta(conv, platform):
    if platform == 'claude':
        return conv.get('uuid', ''), conv.get('name', 'Untitled'), conv.get('created_at', ''), conv.get('updated_at', '')
    elif platform == 'chatgpt':
        return conv.get('id', ''), conv.get('title', 'Untitled'), str(conv.get('create_time', '')), str(conv.get('update_time', ''))
    return '', 'Untitled', '', ''

def build_context(conv, platform):
    """Strategy C: send the full user-message text when it fits within
    CONTEXT_BUDGET characters; fall back to stratified sampling for long
    conversations so topic drift is still visible to the classifier."""
    uuid, name, created, updated = get_conv_meta(conv, platform)
    msgs = get_messages(conv, platform)
    total = len(conv.get('chat_messages', conv.get('mapping', {})))

    texts = [get_text(m, platform).strip() for m in msgs]
    texts = [t for t in texts if t]
    n = len(texts)

    if n == 0:
        return uuid, name, created, updated, total, f"Title: {name}\nTotal messages: {total}\n\n(no user text)"

    full_body = '\n\n'.join(f"[{i+1}] {t}" for i, t in enumerate(texts))

    if len(full_body) <= CONTEXT_BUDGET:
        body = full_body
        coverage = f"full ({n} messages)"
    elif n <= SAMPLE_N:
        # Few but very long messages — truncate each proportionally
        per_msg = max(200, CONTEXT_BUDGET // n)
        body = '\n\n'.join(f"[{i+1}] {t[:per_msg]}" for i, t in enumerate(texts))
        coverage = f"truncated ({n} messages, ~{per_msg} chars each)"
    else:
        # Stratified sample: SAMPLE_N evenly-spaced messages across the arc
        indices = sorted({int(i * (n - 1) / (SAMPLE_N - 1)) for i in range(SAMPLE_N)})
        per_msg = max(200, CONTEXT_BUDGET // len(indices))
        body = '\n\n'.join(f"[{idx+1}/{n}] {texts[idx][:per_msg]}" for idx in indices)
        coverage = f"sampled ({len(indices)} of {n} messages, ~{per_msg} chars each)"

    ctx = f"Title: {name}\nTotal user messages: {n} (coverage: {coverage})\n\nMessages:\n{body}"
    return uuid, name, created, updated, total, ctx

PROMPT = """Classify this AI conversation into EXACTLY ONE Layer 1 category and
EXACTLY ONE Layer 2 category, then summarise what it was actually about.
Consider the whole arc — opening, middle, and closing — not just the first message.
If the conversation spans multiple themes, pick the dominant one.

LAYER 1:
- Writing (drafting, editing, feedback, grammar, rewriting)
- Research (fact-finding, analysis, synthesis, market research)
- Coding (debugging, building, explaining, reviewing code)
- Strategy (brainstorming, planning, decision support, frameworks)
- Learning (understanding concepts, explanations, summaries)
- Creative (fiction, storytelling, creative ideation)
- Personal (reflection, life decisions, health, relationships)
- Admin (emails, formatting, templates, quick lookups)

LAYER 2 per Layer 1:
Writing → [Drafting, Editing, Grammar, Feedback, Rewriting, Summarising]
Research → [Fact finding, Competitive analysis, Policy analysis, Market research, Synthesis]
Coding → [Debugging, Building, Explanation, Review, Architecture]
Strategy → [Brainstorming, Decision support, Planning, Frameworks, Evaluation]
Learning → [Concept explanation, How-to, Deep dive, Comparison]
Creative → [Fiction, Ideation, Worldbuilding, Scriptwriting]
Personal → [Reflection, Health, Life decisions, Relationships]
Admin → [Email, Formatting, Templates, Quick lookup]

SUMMARY: one or two short sentences describing what the conversation was
actually about. Be concrete (e.g., "Debugging React useEffect dependency loop"
rather than "Coding question"). Reflect topic drift if the conversation moved.

KEY_THEMES: 2-4 short lowercase noun phrases or entities (e.g., "react",
"redux migration", "pricing", "hiring"). No sentences.

CONVERSATION:
{context}

Respond ONLY with valid JSON, no explanation, no markdown fences. `layer1` and
`layer2` MUST be single strings (one category each), not lists or comma-joined.
`key_themes` MUST be a JSON array of 2-4 short strings.
{{"layer1": "Strategy", "layer2": "Planning", "confidence": "high|medium|low", "summary": "...", "key_themes": ["theme1", "theme2"]}}"""

# ── Classify ──────────────────────────────────────────────────────────────────
results = []

for conv in tqdm(conversations, desc="Classifying"):
    uuid, name, created, updated, total, context = build_context(conv, platform)

    if not uuid or uuid in done_uuids:
        continue

    # Apply time filter
    if cutoff and created:
        try:
            conv_date = pd.Timestamp(created, tz='UTC')
            if conv_date < pd.Timestamp(cutoff, tz='UTC'):
                continue
        except:
            pass

    try:
        response = ollama.chat(
            model='mistral',
            messages=[{'role': 'user', 'content': PROMPT.format(context=context)}]
        )
        raw = response['message']['content'].strip()
        if '```' in raw:
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        parsed = json.loads(raw)

        def _first_label(v, default='Unknown'):
            if isinstance(v, list):
                v = v[0] if v else default
            v = str(v).strip()
            # If model returned "Strategy, Admin" or "Strategy/Admin", keep the first
            for sep in (',', '/', ';', '|'):
                if sep in v:
                    v = v.split(sep)[0].strip()
                    break
            return v or default

        layer1 = _first_label(parsed.get('layer1'))
        layer2 = _first_label(parsed.get('layer2'))
        confidence = parsed.get('confidence', 'medium')
        summary = str(parsed.get('summary', '') or '').strip().replace('\n', ' ')
        raw_themes = parsed.get('key_themes', []) or []
        if isinstance(raw_themes, str):
            raw_themes = [t for t in raw_themes.replace(',', ';').split(';')]
        themes = [str(t).strip().lower() for t in raw_themes if str(t).strip()]
        key_themes = ';'.join(themes[:5])
    except Exception:
        layer1 = 'Unknown'
        layer2 = 'Unknown'
        confidence = 'low'
        summary = ''
        key_themes = ''

    results.append({
        'uuid': uuid,
        'name': name,
        'created_at': created,
        'updated_at': updated,
        'message_count': total,
        'layer1': layer1,
        'layer2': layer2,
        'confidence': confidence,
        'summary': summary,
        'key_themes': key_themes,
    })

    if len(results) % 10 == 0:
        batch = pd.DataFrame(results)
        combined = pd.concat([existing, batch], ignore_index=True)
        combined = combined.reindex(columns=CSV_COLUMNS)
        combined.to_csv(SAVE_PATH, index=False)

if results:
    batch = pd.DataFrame(results)
    combined = pd.concat([existing, batch], ignore_index=True)
    combined = combined.reindex(columns=CSV_COLUMNS)
    combined.to_csv(SAVE_PATH, index=False)
    print(f"\nDone. {len(combined)} conversations classified.")
    print(f"\nLayer 1 distribution:")
    print(combined['layer1'].value_counts().to_string())
    print(f"\nNext step: python3 report.py")
else:
    print("Nothing new to classify.")
