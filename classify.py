import json
import os
import pandas as pd
import ollama
from tqdm import tqdm

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, 'config.json')
DATA_PATH = os.path.join(BASE, 'data', 'conversations.json')
SAVE_PATH = os.path.join(BASE, 'classified.csv')

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
    done_uuids = set(existing['uuid'].tolist())
    print(f"Resuming — {len(done_uuids)} done, {len(conversations) - len(done_uuids)} remaining.")
else:
    existing = pd.DataFrame()
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
    uuid, name, created, updated = get_conv_meta(conv, platform)
    msgs = get_messages(conv, platform)
    total = len(conv.get('chat_messages', conv.get('mapping', {})))
    first = msgs[:3]
    last = msgs[-2:] if len(msgs) > 3 else []
    ctx = f"Title: {name}\nTotal messages: {total}\n\nFirst messages:\n"
    for i, m in enumerate(first):
        ctx += f"{i+1}. {get_text(m, platform)[:400]}\n"
    if last:
        ctx += "\nLast messages:\n"
        for i, m in enumerate(last):
            ctx += f"{i+1}. {get_text(m, platform)[:400]}\n"
    return uuid, name, created, updated, total, ctx

PROMPT = """Classify this AI conversation into exactly one Layer 1 and one Layer 2 category.

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

CONVERSATION:
{context}

Respond ONLY with valid JSON, no explanation:
{{"layer1": "...", "layer2": "...", "confidence": "high|medium|low"}}"""

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
        layer1 = parsed.get('layer1', 'Unknown')
        layer2 = parsed.get('layer2', 'Unknown')
        confidence = parsed.get('confidence', 'medium')
    except:
        layer1 = 'Unknown'
        layer2 = 'Unknown'
        confidence = 'low'

    results.append({
        'uuid': uuid,
        'name': name,
        'created_at': created,
        'updated_at': updated,
        'message_count': total,
        'layer1': layer1,
        'layer2': layer2,
        'confidence': confidence,
    })

    if len(results) % 10 == 0:
        batch = pd.DataFrame(results)
        combined = pd.concat([existing, batch], ignore_index=True)
        combined.to_csv(SAVE_PATH, index=False)

if results:
    batch = pd.DataFrame(results)
    combined = pd.concat([existing, batch], ignore_index=True)
    combined.to_csv(SAVE_PATH, index=False)
    print(f"\nDone. {len(combined)} conversations classified.")
    print(f"\nLayer 1 distribution:")
    print(combined['layer1'].value_counts().to_string())
    print(f"\nNext step: python3 report.py")
else:
    print("Nothing new to classify.")
