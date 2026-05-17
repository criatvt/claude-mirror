import json
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
import numpy as np
import ollama
import markdown
from datetime import datetime
import warnings
import base64
import io
warnings.filterwarnings('ignore')

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, 'config.json')
CLASSIFIED_PATH = os.path.join(BASE, 'classified.csv')
OUTPUT_PATH = os.path.join(BASE, 'output')
os.makedirs(OUTPUT_PATH, exist_ok=True)

if not os.path.exists(CONFIG_PATH):
    print("\n  Run python3 onboarding.py first.\n")
    exit(1)

with open(CONFIG_PATH) as f:
    config = json.load(f)

name = config['name']
print(f"\n  Claude Mirror\n  Generating report for {name}...\n")

# ── Design System ─────────────────────────────────────────────────────────────
# Editorial / New Yorker register — typography-led, light mode, serif body.
# Watercolour-muted earthtones throughout. Terracotta carries the visual
# hierarchy. Body text uses warm-black; charts use deep walnut (never pure
# black) so the eye reads ink-on-paper, not data-on-screen.
BG        = '#FBFAF6'   # warm white — fresh-paper cream
WHITE     = '#FFFFFF'
INK       = '#1E1A14'   # warm-black body text
CHART_DEEP = '#3D2E20'  # deep walnut — chart anchor, never pure black
MUTED     = '#6B5D4A'   # captions, eyebrows, footer
HAIRLINE  = '#E5DFD0'   # card borders, dividers
TERRACOTTA = '#B85A3D'  # accent — hero rule, italic wordmark, stat numbers
# Legacy aliases kept for matplotlib rcParams below
PRUSSIAN  = INK
UMBER     = MUTED
VERDIGRIS = TERRACOTTA

PALETTE = [
    '#3D2E20',   # deep walnut
    '#B85A3D',   # terracotta
    '#708C6B',   # sage
    '#C89B5E',   # ochre
    '#7A4458',   # plum
    '#5C8A8B',   # teal
    '#9B5836',   # rust
    '#4F5E3F',   # moss
]

LAYER1_ORDER = ['Writing', 'Strategy', 'Learning', 'Creative',
                'Research', 'Coding', 'Personal', 'Admin']

# ── Load & clean ──────────────────────────────────────────────────────────────
df = pd.read_csv(CLASSIFIED_PATH)
# Surface stragglers from old CSVs (pre-schema runs may have out-of-taxonomy
# values). With the schema in classify.py these should be zero on fresh runs.
oot = df[~df['layer1'].isin(LAYER1_ORDER)]['layer1'].value_counts()
if len(oot) > 0:
    print(f"  ⚠ {oot.sum()} rows have out-of-taxonomy layer1 — re-run classify.py:")
    for label, count in oot.items():
        print(f"      {label!r}: {count}")
df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
df['month_dt'] = df['created_at'].dt.to_period('M').dt.to_timestamp()
# Hour-of-day and day-of-week reflect the user's wall clock, not UTC.
# Filtering against cutoff_date continues to use the UTC `created_at` column.
_local_now = datetime.now().astimezone()
LOCAL_TZ = _local_now.tzinfo
_offset = _local_now.strftime('%z')  # e.g. '+0530'
TZ_LABEL = f"UTC{_offset[:3]}:{_offset[3:]}" if _offset else 'UTC'
df['created_local'] = df['created_at'].dt.tz_convert(LOCAL_TZ)
df['hour'] = df['created_local'].dt.hour
df['dayofweek'] = df['created_local'].dt.day_name()
df['layer1'] = pd.Categorical(df['layer1'], categories=LAYER1_ORDER, ordered=True)

# ── Apply period filter ───────────────────────────────────────────────────────
cutoff = config.get('cutoff_date') or config.get('start_date')
if cutoff:
    cutoff_ts = pd.Timestamp(cutoff, tz='UTC')
    df = df[df['created_at'] >= cutoff_ts]
    print(f"  Filtered to {len(df)} conversations from {cutoff[:10]} onwards.")

total       = len(df)
date_min    = df['created_at'].min().date()
date_max    = df['created_at'].max().date()
days        = (df['created_at'].max() - df['created_at'].min()).days
avg_msg     = df['message_count'].mean()
max_msg     = int(df['message_count'].max())
peak_month  = df.groupby('month_dt').size().idxmax().strftime('%b %Y')
peak_count  = int(df.groupby('month_dt').size().max())
common_day  = df['dayofweek'].value_counts().idxmax()
common_hour = int(df['hour'].value_counts().idxmax())
top_cat     = str(df['layer1'].value_counts().idxmax())

plt.rcParams.update({
    'font.family'      : 'DejaVu Serif',
    'figure.facecolor' : BG,
    'axes.facecolor'   : BG,
    'axes.edgecolor'   : PRUSSIAN,
    'axes.labelcolor'  : PRUSSIAN,
    'xtick.color'      : PRUSSIAN,
    'ytick.color'      : PRUSSIAN,
    'text.color'       : PRUSSIAN,
    'grid.alpha'       : 0.3,
    'grid.color'       : PRUSSIAN,
})

def fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return b64

charts = {}

# Chart 1 — Donut
fig, ax = plt.subplots(figsize=(8, 8), facecolor=BG)
counts = df['layer1'].value_counts()
donut_total = int(counts.sum())
wedges, _texts, autotexts = ax.pie(
    counts.values,
    autopct=lambda p: f'{p:.0f}%' if p >= 6 else '',
    colors=PALETTE[:len(counts)],
    wedgeprops={'width': 0.55, 'edgecolor': BG, 'linewidth': 3},
    pctdistance=0.78, startangle=90)
for a in autotexts:
    a.set_fontsize(10); a.set_fontweight('bold'); a.set_color(BG)
ax.set_title('Overall Distribution', fontsize=15, fontweight='bold', color=PRUSSIAN, pad=16)
legend_labels = [f'{cat}  ·  {cnt}  ({cnt/donut_total*100:.1f}%)'
                 for cat, cnt in counts.items()]
ax.legend(wedges, legend_labels, loc='upper center',
          bbox_to_anchor=(0.5, -0.02), ncol=2, frameon=False, fontsize=10,
          handlelength=1.4, columnspacing=2.4, handletextpad=0.8)
plt.tight_layout()
charts['donut'] = fig_to_b64(fig)
print("  ✓ Chart 1: Donut")

# Chart 2 — Monthly volume (categorical x-axis so bars don't overflow on short ranges)
fig, ax = plt.subplots(figsize=(14, 5), facecolor=BG)
monthly = df.groupby('month_dt').size().reset_index(name='count')
month_labels = [d.strftime('%b %Y') for d in monthly['month_dt']]
bar_width = min(0.6, 0.18 + 0.42 * max(0, (12 - len(monthly)) / 12))
bars = ax.bar(month_labels, monthly['count'], color=PRUSSIAN, alpha=0.85,
              width=bar_width, zorder=3)
for bar in bars:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
            str(int(bar.get_height())), ha='center', va='bottom', fontsize=9, color=PRUSSIAN)
ax.set_title('Conversations Per Month', fontsize=15, fontweight='bold', color=PRUSSIAN)
ax.set_xlabel('Month', fontsize=11); ax.set_ylabel('Conversations', fontsize=11)
ax.yaxis.grid(True, linestyle='--', alpha=0.4, zorder=0); ax.set_axisbelow(True)
plt.xticks(rotation=45 if len(monthly) > 4 else 0, ha='right' if len(monthly) > 4 else 'center')
plt.tight_layout()
charts['monthly'] = fig_to_b64(fig)
print("  ✓ Chart 2: Monthly volume")

# Chart 3 — Stacked monthly (categorical x-axis matches Chart 2)
fig, ax = plt.subplots(figsize=(14, 6), facecolor=BG)
pivot = df.groupby(['month_dt', 'layer1']).size().unstack(fill_value=0)
pivot = pivot.reindex(columns=LAYER1_ORDER, fill_value=0)
stack_labels = [d.strftime('%b %Y') for d in pivot.index]
stack_width = min(0.6, 0.18 + 0.42 * max(0, (12 - len(pivot)) / 12))
bottom = np.zeros(len(pivot))
for i, col in enumerate(pivot.columns):
    vals = pivot[col].values
    ax.bar(stack_labels, vals, bottom=bottom, label=col,
           color=PALETTE[i], width=stack_width, alpha=0.9, zorder=3)
    bottom += vals
ax.set_title('Topic Mix Over Time', fontsize=15, fontweight='bold', color=PRUSSIAN)
ax.set_xlabel('Month', fontsize=11); ax.set_ylabel('Conversations', fontsize=11)
ax.legend(loc='upper left', fontsize=9, framealpha=0.9)
ax.yaxis.grid(True, linestyle='--', alpha=0.4, zorder=0); ax.set_axisbelow(True)
plt.xticks(rotation=45 if len(pivot) > 4 else 0, ha='right' if len(pivot) > 4 else 'center')
plt.tight_layout()
charts['stacked'] = fig_to_b64(fig)
print("  ✓ Chart 3: Stacked monthly")

# Chart 4 — Heatmap
fig, ax = plt.subplots(figsize=(14, 5), facecolor=BG)
days_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
hm = df.groupby(['dayofweek','hour']).size().unstack(fill_value=0)
hm = hm.reindex(days_order, fill_value=0)
sns.heatmap(hm, ax=ax, cmap=sns.light_palette(PRUSSIAN, as_cmap=True),
            linewidths=0.5, linecolor=BG, cbar_kws={'label': 'Conversations'})
ax.set_title(f'When You Use Claude ({TZ_LABEL})', fontsize=15, fontweight='bold', color=PRUSSIAN)
ax.set_xlabel(f'Hour of Day ({TZ_LABEL})', fontsize=11); ax.set_ylabel('')
plt.tight_layout()
charts['heatmap'] = fig_to_b64(fig)
print("  ✓ Chart 4: Heatmap")

# Chart 5 — Depth
fig, ax = plt.subplots(figsize=(10, 5), facecolor=BG)
ax.hist(df['message_count'], bins=30, color=PRUSSIAN, alpha=0.8, edgecolor=BG, zorder=3)
ax.axvline(df['message_count'].mean(), color=UMBER, linestyle='--', linewidth=2,
           label=f"Mean: {df['message_count'].mean():.1f}")
ax.axvline(df['message_count'].median(), color=VERDIGRIS, linestyle='--', linewidth=2,
           label=f"Median: {df['message_count'].median():.1f}")
ax.set_title('Conversation Depth', fontsize=15, fontweight='bold', color=PRUSSIAN)
ax.set_xlabel('Messages per Conversation', fontsize=11); ax.set_ylabel('Frequency', fontsize=11)
ax.legend(fontsize=10)
ax.yaxis.grid(True, linestyle='--', alpha=0.4, zorder=0); ax.set_axisbelow(True)
plt.tight_layout()
charts['depth'] = fig_to_b64(fig)
print("  ✓ Chart 5: Depth")

# Chart 6 — Layer 2
fig, axes = plt.subplots(2, 4, figsize=(18, 9), facecolor=BG)
axes = axes.flatten()
for i, cat in enumerate(LAYER1_ORDER):
    ax = axes[i]
    sub = df[df['layer1'] == cat]['layer2'].value_counts().head(5)
    if len(sub) == 0:
        ax.set_visible(False); continue
    bars = ax.barh(sub.index, sub.values, color=PALETTE[i], alpha=0.85)
    ax.set_title(cat, fontsize=12, fontweight='bold', color=PALETTE[i])
    ax.set_xlabel('Count', fontsize=9)
    ax.xaxis.grid(True, linestyle='--', alpha=0.4); ax.set_axisbelow(True)
    for bar, val in zip(bars, sub.values):
        ax.text(val + 0.1, bar.get_y() + bar.get_height()/2, str(val), va='center', fontsize=8)
fig.suptitle('What You Do Within Each Category', fontsize=15, fontweight='bold', color=PRUSSIAN, y=1.01)
plt.tight_layout()
charts['layer2'] = fig_to_b64(fig)
print("  ✓ Chart 6: Layer 2")

# Chart 7 — Trends
fig, ax = plt.subplots(figsize=(14, 6), facecolor=BG)
for i, cat in enumerate(LAYER1_ORDER):
    cm = df[df['layer1'] == cat].groupby('month_dt').size().reset_index(name='count')
    if len(cm) < 2: continue
    ax.plot(cm['month_dt'], cm['count'], marker='o', markersize=5,
            linewidth=2.5, label=cat, color=PALETTE[i], alpha=0.9)
ax.set_title('Category Trends Over Time', fontsize=15, fontweight='bold', color=PRUSSIAN)
ax.set_xlabel('Month', fontsize=11); ax.set_ylabel('Conversations', fontsize=11)
ax.legend(loc='upper left', fontsize=9, framealpha=0.9)
ax.yaxis.grid(True, linestyle='--', alpha=0.4); ax.set_axisbelow(True)
plt.xticks(rotation=45, ha='right'); plt.tight_layout()
charts['trends'] = fig_to_b64(fig)
print("  ✓ Chart 7: Trends")

# Chart 8 — Word cloud
fig, ax = plt.subplots(figsize=(14, 6), facecolor=BG)
titles_text = ' '.join(df['name'].dropna().tolist())
stopwords = {'and','the','for','with','how','to','a','an','in','of','on',
             'is','my','me','i','it','using','use','help','can','from',
             'this','that','about','at','be'}
wc = WordCloud(width=1400, height=600, background_color=BG, colormap='copper',
               stopwords=stopwords, max_words=100,
               prefer_horizontal=0.85).generate(titles_text)
ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
ax.set_title('What You Talk About', fontsize=15, fontweight='bold', color=PRUSSIAN, pad=15)
plt.tight_layout()
charts['wordcloud'] = fig_to_b64(fig)
print("  ✓ Chart 8: Word cloud")

# ── Brief ─────────────────────────────────────────────────────────────────────
print("\n  Generating your personal brief (3-5 mins)...")

l1_dist = df['layer1'].value_counts().to_dict()
l2 = {cat: df[df['layer1'] == cat]['layer2'].value_counts().head(5).to_dict()
      for cat in LAYER1_ORDER}
monthly_str = {str(k.date()): int(v) for k, v in df.groupby('month_dt').size().items()}
longest = df.nlargest(3, 'message_count')[['name','message_count','layer1']].to_dict('records')

# ── Per-category themes & sample summaries (issue #9) ─────────────────────────
from collections import Counter

has_summary = 'summary' in df.columns
has_themes = 'key_themes' in df.columns

if not (has_summary and has_themes):
    print("  ⚠ classified.csv is missing 'summary'/'key_themes' columns — "
          "re-run classify.py to enrich the brief with specific themes.")

themes_per_cat = {}
samples_per_cat = {}

for cat in LAYER1_ORDER:
    sub = df[df['layer1'] == cat]
    if len(sub) == 0:
        continue

    if has_themes:
        counter = Counter()
        for raw in sub['key_themes'].dropna().tolist():
            for t in str(raw).split(';'):
                t = t.strip().lower()
                if t:
                    counter[t] += 1
        top = [t for t, _ in counter.most_common(6)]
        if top:
            themes_per_cat[cat] = top

    if has_summary:
        # Prefer summaries from the longest conversations in each category
        ordered = sub.sort_values('message_count', ascending=False)
        picks = []
        for s in ordered['summary'].dropna().tolist():
            s = str(s).strip()
            if s and s.lower() not in ('nan', 'none') and s not in picks:
                picks.append(s)
            if len(picks) >= 4:
                break
        if picks:
            samples_per_cat[cat] = picks

if themes_per_cat:
    themes_block = '\n'.join(f"- {cat}: {', '.join(ts)}" for cat, ts in themes_per_cat.items())
else:
    themes_block = "(no theme data — classified.csv predates the summary/key_themes columns)"

if samples_per_cat:
    sample_lines = []
    for cat, picks in samples_per_cat.items():
        sample_lines.append(f"- {cat}:")
        for s in picks:
            sample_lines.append(f"    • {s}")
    samples_block = '\n'.join(sample_lines)
else:
    samples_block = "(no per-conversation summaries — re-run classify.py to enable)"

BRIEF_PROMPT = f"""You are writing a thoughtful, direct, slightly literary
reflection for a real person on what their AI usage shows about them. Speak
like a careful friend who has read everything, not like a consultant. Avoid
corporate or coaching vocabulary ("leverage", "optimise", "actionable",
"unlock", "journey"). British English.

Be tight. Total ≤ 600 words. Every section has a hard cap below — respect
it. If a section can be said in fewer words, use fewer. Cut filler, hedging, and
restatement. Prefer one sharp sentence over three soft ones.

ABOUT THIS PERSON:
- Name: {name}
- Profession: {config['profession']}
- Current top goal: {config['goal']}
- Period analysed: {config.get('period', config.get('period_label', 'All available data'))}

USAGE DATA:
- Total conversations: {total}
- Date range: {date_min} to {date_max} ({days} days)
- Average messages per conversation: {avg_msg:.1f}
- Longest conversation: {max_msg} messages
- Peak month: {peak_month} ({peak_count} conversations)
- Most active day: {common_day} at {common_hour}:00
- Top category: {top_cat}

CATEGORY DISTRIBUTION:
{json.dumps(l1_dist, indent=2)}

LAYER 2 BREAKDOWN:
{json.dumps(l2, indent=2)}

MONTHLY VOLUME:
{json.dumps(monthly_str, indent=2)}

TOP 3 LONGEST CONVERSATIONS:
{json.dumps(longest, indent=2)}

COMMON THEMES PER CATEGORY (derived from per-conversation key_themes):
{themes_block}

SAMPLE CONVERSATIONS PER CATEGORY (verbatim summaries — what these conversations actually look like):
{samples_block}

When discussing patterns, cite specific recurring themes and conversation
examples from the data above. Do not rely only on category counts — name the
real topics (e.g., "react performance", "pricing models") and reference what
the conversations were about.

The brief has TWO layers. Write them in this exact order, with the exact
separator line shown.

PULL-QUOTE MARKING — VERY IMPORTANT:
EVERY section below is **flowing prose** — never bulleted lists, never
numbered lists. Each section opens with its sharpest sentence wrapped in
`[[hl]]` and `[[/hl]]` markers, then 1-2 sentences of supporting context.

The markers are LITERAL strings: open with two square brackets, then `hl`,
then two square brackets. Close with two square brackets, slash, `hl`, two
square brackets. Like this skeleton (do NOT copy the words, only the shape):

## <section title>
[[hl]]<the sharpest single sentence for this section>[[/hl]]
<1-2 sentences of supporting prose>

Exactly one pull-quote pair per section. Both opening AND closing markers
must be present and well-formed. Do NOT use bullets (- or *) or numbered
lists (1. 2. 3.) anywhere in the brief.

PART A — OBSERVATIONS FROM YOUR DATA
Part A must be specific even if the user's stated goal is generic or vague.
HARD RULE: in Part A, do NOT mention the goal, do NOT use the words "goal",
"objective", or "aspiration", and do NOT frame observations as relative to
what the user is trying to achieve. Part A stands on what the data shows,
nothing else. The goal exists only for Part B.
Open Part A with the italic label below.

*Part A — Observations from your data*

## The story so far
Narrative of their usage arc. Specific numbers. Do not reference the goal here.
**Cap: ≤ 90 words.**

## What this says about you
What this pattern reveals about how they think and work.
**Cap: ≤ 70 words.**

## What stood out
What is unexpected or counterintuitive in this data. Flowing prose, NOT a
bulleted list. Open with the pull-quote sentence, then add 1-2 sentences of
supporting context.
**Cap: ≤ 75 words.**

## One uncomfortable truth
One uncomfortable but important thing the data reveals.
**Cap: ≤ 40 words.**

---

PART B — THROUGH THE LENS OF YOUR GOAL
Part B interprets the observations through the user's stated goal. If the
goal is generic or thin, Part B is allowed to be short. Do NOT pad with
filler. Open Part B with the italic label below.

*Part B — Through the lens of your goal*

## What's missing
What they are NOT using AI for that someone with their goal should be.
Flowing prose, NOT a bulleted list. Open with the pull-quote sentence,
then 1-2 sentences of supporting context.
**Cap: ≤ 75 words.**

## Worth trying
Specific recommendations tied to their profession and goal. No corporate
verbs. Flowing prose, NOT a numbered list. Open with the pull-quote
sentence naming the strongest recommendation, then 1-2 sentences of
supporting context (which may name secondary recommendations inline).
**Cap: ≤ 95 words.**

## Where this is heading
Where their usage is going if they continue on this path.
**Cap: ≤ 50 words.**

Be direct, specific, intelligent. No generic advice. British English.

Before finishing, reread your draft. Check that:
1. Every section is within its cap.
2. Total is within 600 words.
3. EVERY section contains exactly one `[[hl]]...[[/hl]]` pull-quote marker.
   If any section is missing one, add it now around its sharpest sentence.
4. The "Cap:" lines, the "PART A"/"PART B" instruction blocks, and the
   "PULL-QUOTE MARKING" instructions are NOT in your output — those are
   instructions to you, not part of the brief.

Emit only the italic labels, the `---` separator, the section headers, the
prose, and the `[[hl]]...[[/hl]]` markers."""

resp = ollama.chat(
    model='mistral',
    messages=[{'role': 'user', 'content': BRIEF_PROMPT}],
    options={'num_predict': 3000, 'temperature': 0.7}
)
brief_md_raw = resp['message']['content']

# ── Pull-quote post-processing (#6) ───────────────────────────────────────────
# Model is instructed to mark one sentence per section with [[hl]]...[[/hl]].
# Small local models often skip the instruction, so we fall back to an
# algorithmic marker pass that wraps the longest sentence in each section.
# In HTML the markers become styled pull-quote blocks (New Yorker convention).
# In Markdown they become blockquote+italic for clean rendering on GitHub.
import re as _re_hl

# Tolerant marker pattern — accepts the model's occasional single-bracket
# slips (`[hl]` / `[/hl]`) as well as the canonical double-bracket form.
_hl_pattern = _re_hl.compile(
    r'\[{1,2}hl\]{1,2}(.+?)\[{1,2}/hl\]{1,2}', _re_hl.DOTALL
)
# Stragglers that survive substitution (e.g. unmatched opening or closing)
_hl_straggler = _re_hl.compile(r'\[{1,2}/?hl\]{1,2}')


def _add_fallback_pullquotes(md):
    """If a section has no [[hl]] markers, wrap its longest prose sentence.
    Skips list items (bulleted, numbered) and blockquotes so the marker
    never ends up nested inside an <li>."""
    parts = _re_hl.split(r'(?m)^(##\s.+)$', md)
    if len(parts) < 3:
        return md
    list_or_quote = _re_hl.compile(r'^\s*([-*•]|\d+[.)]|>)')
    out = [parts[0]]
    for i in range(1, len(parts), 2):
        heading = parts[i]
        body = parts[i + 1] if (i + 1) < len(parts) else ''
        if '[[hl]]' in body:
            out.extend([heading, body]); continue
        # Filter body to prose lines only — drop bullets, numbered items, quotes
        prose_only = '\n'.join(
            ln for ln in body.split('\n') if not list_or_quote.match(ln)
        )
        candidates = _re_hl.findall(r'[A-Z][^.!?]*[.!?](?=\s|$)', prose_only)
        candidates = [c.strip() for c in candidates if len(c.strip()) > 30]
        if not candidates:
            out.extend([heading, body]); continue
        longest = max(candidates, key=len)
        body = body.replace(longest, f'[[hl]]{longest}[[/hl]]', 1)
        out.extend([heading, body])
    return ''.join(out)


brief_md_raw = _add_fallback_pullquotes(brief_md_raw)

# Markdown export — turn marker into a blockquote line
brief_md = _hl_pattern.sub(lambda m: f'\n\n> *{m.group(1).strip()}*\n\n', brief_md_raw)
# Strip any unmatched marker stragglers from the markdown
brief_md = _hl_straggler.sub('', brief_md)

# HTML — render markdown first (with markers intact), then replace markers
# with a styled blockquote that breaks out of the current <p> cleanly.
_html_pre = markdown.markdown(brief_md_raw, extensions=['extra'])
def _hl_to_card(m):
    text = m.group(1).strip()
    return f'</p><blockquote class="hl-card">{text}</blockquote><p>'
brief_html = _hl_pattern.sub(_hl_to_card, _html_pre)
# Strip any unmatched marker stragglers from the HTML too
brief_html = _hl_straggler.sub('', brief_html)
# Clean up any empty paragraphs the substitution may have produced
brief_html = _re_hl.sub(r'<p>\s*</p>', '', brief_html)
print("  ✓ Brief generated")

# ── HTML ──────────────────────────────────────────────────────────────────────
print("\n  Building report...")
now_str = datetime.now().strftime('%B %d, %Y')

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — Claude Mirror</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&display=swap" rel="stylesheet">
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: 'Cormorant Garamond', Georgia, 'Times New Roman', serif;
  background: #FBFAF6;
  color: #1E1A14;
  line-height: 1.55;
  font-size: 18px;
}}
.container {{
  max-width: 1020px;
  margin: 0 auto;
  padding: 72px 60px;
}}
/* ─── Hero: typography-led, light page, no colour block ─── */
.hero {{
  padding: 8px 0 64px;
  border-bottom: 1px solid #1E1A14;
  margin-bottom: 72px;
}}
.hero-rule {{
  width: 56px;
  height: 3px;
  background: #B85A3D;
  margin-bottom: 32px;
}}
.hero-eyebrow {{
  font-size: 0.7em;
  letter-spacing: 5px;
  text-transform: uppercase;
  color: #6B5D4A;
  margin-bottom: 20px;
  font-weight: 500;
}}
.hero h1 {{
  font-size: 4.4em;
  font-weight: 600;
  line-height: 0.95;
  letter-spacing: -1.5px;
  margin: 0 0 4px;
  color: #1E1A14;
}}
.hero h1 span {{ color: #B85A3D; font-style: italic; font-weight: 500; }}
.hero-meta {{
  font-size: 0.88em;
  color: #6B5D4A;
  font-style: italic;
  margin: 28px 0 40px;
  max-width: 720px;
}}
.stats-row {{
  display: flex;
  flex-wrap: wrap;
  gap: 48px;
}}
.stat-card {{
  background: none;
  border: none;
  padding: 0;
  min-width: 0;
}}
.stat-number {{
  font-size: 2.4em;
  font-weight: 600;
  color: #B85A3D;
  display: block;
  line-height: 1;
  font-feature-settings: "lnum";
}}
.stat-label {{
  font-size: 0.6em;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  color: #6B5D4A;
  margin-top: 8px;
  display: block;
}}
/* ─── Sections ─── */
.section {{ margin-bottom: 80px; }}
.section-eyebrow {{
  font-size: 0.68em;
  letter-spacing: 4px;
  text-transform: uppercase;
  color: #6B5D4A;
  margin-bottom: 8px;
}}
.section-title {{
  font-size: 2.4em;
  font-weight: 600;
  margin: 0 0 8px;
  line-height: 1.05;
  letter-spacing: -0.8px;
  color: #1E1A14;
}}
.section-desc {{
  color: #6B5D4A;
  font-style: italic;
  font-size: 1.06em;
  margin: 0 0 36px;
  max-width: 640px;
}}
/* ─── Cards ─── */
.card {{
  background: #FFFFFF;
  border: 1px solid #E5DFD0;
  border-radius: 0;
  padding: 36px;
  margin-bottom: 24px;
}}
.card img {{
  width: 100%;
  display: block;
}}
.card-note {{
  font-size: 0.78em;
  color: #6B5D4A;
  font-style: italic;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #EFE6CE;
}}
.grid-2 {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}}
.divider {{
  height: 1px;
  background: #E5DFD0;
  margin: 64px 0;
}}
/* ─── Brief ─── */
.brief-wrap {{
  background: #FFFFFF;
  border: 1px solid #E5DFD0;
  border-left: 4px solid #B85A3D;
  border-radius: 0;
  padding: 40px 44px;
}}
.brief-wrap h2 {{
  font-size: 1.5em;
  font-weight: 600;
  color: #1E1A14;
  margin: 36px 0 14px;
  line-height: 1.2;
  padding: 0;
  border: none;
}}
.brief-wrap h2:first-of-type {{ margin-top: 8px; }}
.brief-wrap p {{
  color: #1E1A14;
  margin-bottom: 16px;
  line-height: 1.7;
  font-size: 1.0em;
}}
.brief-wrap ul, .brief-wrap ol {{
  padding-left: 24px;
  margin-bottom: 16px;
}}
.brief-wrap li {{
  color: #1E1A14;
  margin-bottom: 8px;
  line-height: 1.7;
}}
.brief-wrap strong {{ color: #6B5D4A; }}
.brief-wrap hr {{
  border: 0;
  border-top: 1px solid #E5DFD0;
  margin: 32px 0 24px;
}}
.brief-wrap p > em:only-child {{
  display: block;
  color: #6B5D4A;
  font-size: 0.7em;
  letter-spacing: 3px;
  text-transform: uppercase;
  font-style: normal;
  margin: 4px 0 12px;
}}
.brief-wrap blockquote {{
  border-left: 2px solid #C89B5E;
  margin: 18px 0;
  padding: 6px 0 6px 20px;
  color: #6B5D4A;
  font-style: italic;
}}
.brief-wrap .hl-card {{
  font-size: 1.55em;
  line-height: 1.35;
  font-style: italic;
  color: #B85A3D;
  border-left: 3px solid #B85A3D;
  margin: 28px 0;
  padding: 12px 0 12px 28px;
  font-weight: 500;
}}
/* Drop cap on the first paragraph after the first h2 in the brief */
.brief-wrap h2:first-of-type + p::first-letter {{
  font-size: 3.6em;
  line-height: 0.85;
  float: left;
  margin: 6px 10px 0 0;
  font-weight: 600;
  color: #B85A3D;
  font-style: italic;
}}
.footer {{
  text-align: center;
  padding: 40px 20px;
  border-top: 1px solid #E5DFD0;
  color: #6B5D4A;
  font-size: 0.85em;
  font-style: italic;
  background: #FBFAF6;
}}
.footer a {{ color: #B85A3D; text-decoration: none; }}
@media (max-width: 768px) {{
  .container {{ padding: 48px 24px; }}
  .hero h1 {{ font-size: 2.6em; }}
  .section-title {{ font-size: 1.9em; }}
  .grid-2 {{ grid-template-columns: 1fr; }}
  .brief-wrap {{ padding: 28px; }}
  .stats-row {{ gap: 28px; }}
}}
</style>
</head>
<body>

<div class="container">

<div class="hero">
  <div class="hero-rule"></div>
  <p class="hero-eyebrow">Claude Mirror &nbsp;&middot;&nbsp; A Personal Reflection</p>
  <h1>{name}'s <span>AI&nbsp;Mirror</span></h1>
  <p class="hero-meta">{config.get('period', config.get('period_label', 'All available data'))} &nbsp;&middot;&nbsp; {date_min} &rarr; {date_max} &nbsp;&middot;&nbsp; Generated {now_str} &nbsp;&middot;&nbsp; Times in {TZ_LABEL}</p>
  <div class="stats-row">
    <div class="stat-card"><span class="stat-number">{total}</span><span class="stat-label">Conversations</span></div>
    <div class="stat-card"><span class="stat-number">{days}</span><span class="stat-label">Days of Data</span></div>
    <div class="stat-card"><span class="stat-number">{avg_msg:.0f}</span><span class="stat-label">Avg Messages</span></div>
    <div class="stat-card"><span class="stat-number">{max_msg}</span><span class="stat-label">Longest Conv.</span></div>
    <div class="stat-card"><span class="stat-number">{peak_month}</span><span class="stat-label">Peak Month</span></div>
    <div class="stat-card"><span class="stat-number">{common_day[:3]}</span><span class="stat-label">Most Active Day</span></div>
  </div>
</div>

  <div class="section">
    <p class="section-eyebrow">Your Usage Story</p>
    <h2 class="section-title">How Your Usage Has Evolved</h2>
    <p class="section-desc">Month by month &mdash; volume and topic mix over your full history.</p>
    <div class="card">
      <img src="data:image/png;base64,{charts['monthly']}" alt="Monthly volume">
      <p class="card-note">Total conversations started per month.</p>
    </div>
    <div class="card">
      <img src="data:image/png;base64,{charts['stacked']}" alt="Topic mix">
      <p class="card-note">How the mix of topics has shifted over time.</p>
    </div>
  </div>

  <div class="divider"></div>

  <div class="section">
    <p class="section-eyebrow">What You Use Claude For</p>
    <h2 class="section-title">Your Usage Breakdown</h2>
    <p class="section-desc">Where you spend your AI time &mdash; and how deep you go.</p>
    <div class="grid-2">
      <div class="card">
        <img src="data:image/png;base64,{charts['donut']}" alt="Distribution">
        <p class="card-note">Overall category distribution.</p>
      </div>
      <div class="card">
        <img src="data:image/png;base64,{charts['depth']}" alt="Depth">
        <p class="card-note">Short tasks vs deep working sessions.</p>
      </div>
    </div>
  </div>

  <div class="divider"></div>

  <div class="section">
    <p class="section-eyebrow">Your Patterns</p>
    <h2 class="section-title">When and How You Work</h2>
    <p class="section-desc">Your rhythm &mdash; by day, by hour, and by topic over time.</p>
    <div class="card">
      <img src="data:image/png;base64,{charts['heatmap']}" alt="Heatmap">
      <p class="card-note">Your most active days and hours.</p>
    </div>
    <div class="card">
      <img src="data:image/png;base64,{charts['trends']}" alt="Trends">
      <p class="card-note">How each category has trended month by month.</p>
    </div>
  </div>

  <div class="divider"></div>

  <div class="section">
    <p class="section-eyebrow">Deep Dive</p>
    <h2 class="section-title">What You Talk About</h2>
    <p class="section-desc">Within each category, and across all your conversation titles.</p>
    <div class="card">
      <img src="data:image/png;base64,{charts['layer2']}" alt="Layer 2">
      <p class="card-note">Task breakdown within each category.</p>
    </div>
    <div class="card">
      <img src="data:image/png;base64,{charts['wordcloud']}" alt="Word cloud">
      <p class="card-note">Most frequent topics from your conversation titles.</p>
    </div>
  </div>

  <div class="divider"></div>

  <div class="section">
    <p class="section-eyebrow">A reflection</p>
    <h2 class="section-title">The Mirror</h2>
    <p class="section-desc">A thoughtful read of your data — written locally by Mistral on your machine.</p>
    <div class="brief-wrap">
      {brief_html}
    </div>
  </div>

</div>

<div class="footer">
  <p>Built by <strong>Aasif Iqbal J.</strong> with <strong>Claude</strong>
  &nbsp;&middot;&nbsp;
  <a href="https://github.com/criatvt/claude-mirror">github.com/criatvt/claude-mirror</a></p>
  <p style="margin-top:6px;">Generated locally on {now_str} &nbsp;&middot;&nbsp; No data left your machine</p>
  <p style="margin-top:16px; font-size:0.78em; color:#8a7060; max-width:700px; margin-left:auto; margin-right:auto; line-height:1.6;">
  <strong>Disclaimer:</strong> This report is generated automatically by Claude Mirror using local AI models. 
  Classifications, insights, and coaching suggestions are algorithmic interpretations of conversation metadata 
  and should not be treated as professional advice of any kind. All analysis is approximate. 
  The accuracy of classifications depends on the AI model used. This tool is intended for personal 
  reflection only.</p>
</div>

</body>
</html>"""

html_path = os.path.join(OUTPUT_PATH, 'report.html')
with open(html_path, 'w') as f:
    f.write(html)
print("  ✓ report.html saved")

# ── Markdown ──────────────────────────────────────────────────────────────────
l1_table = '\n'.join([
    f"| {cat} | {cnt} | {cnt/total*100:.1f}% |"
    for cat, cnt in sorted(l1_dist.items(), key=lambda x: -x[1])
])

md = f"""# Claude Mirror Report
## {name} · {now_str}

> Generated locally from {total} conversations across {days} days.
> No data left your machine.

---

## Key Stats

| Metric | Value |
|--------|-------|
| Total conversations | {total} |
| Date range | {date_min} → {date_max} |
| Days of data | {days} |
| Avg messages / conversation | {avg_msg:.1f} |
| Longest conversation | {max_msg} messages |
| Peak month | {peak_month} ({peak_count} conversations) |
| Most active day | {common_day} |
| Top category | {top_cat} |

---

## Category Distribution

| Category | Count | % |
|----------|-------|---|
{l1_table}

---

## The Mirror

{brief_md}

---

*Built by Aasif Iqbal J. with Claude*
*github.com/criatvt/claude-mirror*
*Re-run monthly to track how your usage evolves.*
"""

md_path = os.path.join(OUTPUT_PATH, 'report.md')
with open(md_path, 'w') as f:
    f.write(md)
print("  ✓ report.md saved")

print(f"""
  =============================================
  Done, {name}!
  Open your report:
  open {html_path}
  =============================================
""")
