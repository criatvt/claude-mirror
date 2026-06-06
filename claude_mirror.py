#!/usr/bin/env python3
"""claude-mirror — single-command entrypoint.

Runs the full pipeline end-to-end:

    python3 claude_mirror.py

It performs friendly prerequisite checks (auto-locating your export if needed),
runs onboarding inline on first use, then calls classify.main() and
report.main() in order. Each prereq failure produces an actionable message
rather than a stack trace.

Note: the three stage modules (onboarding/classify/report) are imported lazily
inside main()/helpers, *after* check_python_deps() runs — importing them eagerly
would pull in pandas/matplotlib/etc. and raise a raw ImportError before we can
print a friendly message.
"""
import datetime
import glob
import json
import os
import shutil
import sys
import urllib.request
import urllib.error

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, 'config.json')
DATA_DIR = os.path.join(BASE, 'data')
DATA_PATH = os.path.join(DATA_DIR, 'conversations.json')
REPORT_HTML = os.path.join(BASE, 'output', 'report.html')

# Where to look for a freshly-downloaded export if it isn't in data/ yet.
SCAN_DIRS = [os.path.expanduser('~/Downloads'), os.path.expanduser('~/Desktop')]

OLLAMA_TAGS_URL = 'http://localhost:11434/api/tags'
MODEL_NAME = 'mistral'  # kept in sync with classify.py; #10 will make this config-driven

# Third-party modules the pipeline needs. (module-to-import, pip-distribution).
REQUIRED_DEPS = [
    ('pandas', 'pandas'),
    ('ollama', 'ollama'),
    ('matplotlib', 'matplotlib'),
    ('seaborn', 'seaborn'),
    ('wordcloud', 'wordcloud'),
    ('markdown', 'markdown'),
    ('numpy', 'numpy'),
    ('dateutil', 'python-dateutil'),
]


def _fail(message):
    """Print a friendly, actionable error and exit non-zero — never a traceback."""
    print(f"\n  ✗ {message}\n")
    sys.exit(1)


def check_python_deps():
    import importlib
    missing = []
    for module_name, _dist in REQUIRED_DEPS:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(module_name)
    if missing:
        _fail(
            "Missing Python packages: " + ", ".join(missing) + "\n"
            "    Install everything with:  pip install -r requirements.txt"
        )


def _fetch_ollama_tags():
    """Return the parsed /api/tags JSON, or None if Ollama is unreachable."""
    try:
        with urllib.request.urlopen(OLLAMA_TAGS_URL, timeout=5) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except (urllib.error.URLError, OSError, ValueError):
        return None


def check_ollama_reachable():
    if _fetch_ollama_tags() is None:
        _fail(
            "Ollama is not running.\n"
            "    Start it with:  ollama serve   (in a separate terminal)"
        )


def check_model_available(name):
    tags = _fetch_ollama_tags()
    if tags is None:
        # Reachability was already checked; treat a late failure as unreachable.
        check_ollama_reachable()
        return

    # Ollama reports names like "mistral:latest"; match on the base name.
    installed = [m.get('name', '') for m in tags.get('models', [])]
    if any(n == name or n.split(':')[0] == name for n in installed):
        return

    print(f"\n  '{name}' isn't pulled yet.")
    try:
        answer = input(f"  Pull it now with `ollama pull {name}`? [Y/n] ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print(
            f"\n\n  Cancelled.\n"
            f"    The '{name}' model is required. Pull it with:  ollama pull {name}\n"
        )
        sys.exit(130)
    if answer in ('', 'y', 'yes'):
        import subprocess
        try:
            subprocess.run(['ollama', 'pull', name], check=True)
        except KeyboardInterrupt:
            print(
                f"\n\n  Pull cancelled.\n"
                f"    Re-run when ready, or pull manually:  ollama pull {name}\n"
            )
            sys.exit(130)
        except (subprocess.CalledProcessError, FileNotFoundError):
            _fail(
                f"Could not pull '{name}'.\n"
                f"    Try manually:  ollama pull {name}"
            )
    else:
        _fail(
            f"The '{name}' model is required to classify conversations.\n"
            f"    Pull it with:  ollama pull {name}"
        )


# ── Smart input detection (#30) ───────────────────────────────────────────────
def _human_size(num_bytes):
    size = float(num_bytes)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == 'B' else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def _describe(path):
    try:
        size = _human_size(os.path.getsize(path))
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d')
        return f"{path}  ({size}, modified {mtime})"
    except OSError:
        return path


def find_conversations_json():
    """Scan common download/desktop locations for a conversations.json export.

    Returns a list of unique candidate paths, most-recently-modified first.
    Covers both a bare file and one nested a single directory deep (e.g. an
    unzipped Claude export like ~/Downloads/data-2026-.../conversations.json).
    """
    found, seen = [], set()
    for d in SCAN_DIRS:
        for pattern in (os.path.join(d, 'conversations.json'),
                        os.path.join(d, '*', 'conversations.json')):
            for path in glob.glob(pattern):
                real = os.path.realpath(path)
                if real in seen or not os.path.isfile(path):
                    continue
                seen.add(real)
                found.append(path)
    found.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return found


def _copy_into_data(src):
    os.makedirs(DATA_DIR, exist_ok=True)
    shutil.copy2(src, DATA_PATH)
    print("  ✓ Copied into data/conversations.json")


def prompt_copy_to_data(candidates):
    """Offer to copy a discovered export into data/. Returns True if copied."""
    try:
        if len(candidates) == 1:
            print(f"\n  Found a conversations export:\n    {_describe(candidates[0])}")
            answer = input("  Copy it into data/? [Y/n] ").strip().lower()
            if answer in ('', 'y', 'yes'):
                _copy_into_data(candidates[0])
                return True
            return False

        print("\n  Found multiple conversation exports:")
        for i, path in enumerate(candidates, 1):
            print(f"    {i}. {_describe(path)}")
        choice = input(f"  Which to use? [1-{len(candidates)}, or n to skip] ").strip().lower()
        if choice.isdigit() and 1 <= int(choice) <= len(candidates):
            _copy_into_data(candidates[int(choice) - 1])
            return True
        return False
    except (KeyboardInterrupt, EOFError):
        print()
        return False


def check_conversations_present():
    if os.path.exists(DATA_PATH):
        return
    # Not in data/ — try to auto-locate a download before giving up.
    candidates = find_conversations_json()
    if candidates and prompt_copy_to_data(candidates) and os.path.exists(DATA_PATH):
        return
    _fail(
        "No conversation data found at data/conversations.json\n"
        f"    Searched: {', '.join(SCAN_DIRS)}\n"
        "    Export your history, then place conversations.json in the data/ folder."
    )


# ── Inline onboarding (#30) ───────────────────────────────────────────────────
def run_onboarding_or_confirm():
    """First run (no config): onboard inline. Returning user: one-press confirm."""
    import onboarding

    if not os.path.exists(CONFIG_PATH):
        print("\n  First-time setup — a few quick questions.")
        onboarding.main()
        return

    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
    except (OSError, ValueError):
        # Unreadable/corrupt config — just re-onboard.
        onboarding.main()
        return

    name = config.get('name', 'there')
    created = (config.get('created_at') or '')[:10]
    when = f" from {created}" if created else ""
    print(f"\n  Welcome back, {name}! Found existing config{when}.")
    try:
        answer = input("  Use existing settings? [Y/n] ").strip().lower()
    except EOFError:
        answer = ''  # non-interactive: keep existing settings
    if answer in ('n', 'no'):
        onboarding.main()


def open_report(path):
    """Open the finished report in the default browser, cross-platform.

    Failures here are non-fatal — the report is already on disk, so we just
    fall back to printing the path for the user to open manually.
    """
    if not os.path.exists(path):
        print(f"  Open manually: {path}")
        return
    import subprocess
    try:
        if sys.platform == 'darwin':
            subprocess.run(['open', path], check=False)
        elif sys.platform.startswith('linux'):
            subprocess.run(['xdg-open', path], check=False)
        elif sys.platform == 'win32':
            subprocess.run(['start', '', path], shell=True, check=False)
        else:
            print(f"  Open manually: {path}")
    except Exception:
        print(f"  Open manually: {path}")


def main():
    print("\n  Claude Mirror — checking prerequisites...")
    check_python_deps()
    check_ollama_reachable()
    check_model_available(MODEL_NAME)
    check_conversations_present()
    print("  ✓ All prerequisites met.")

    # Safe to import the heavy stages now that deps are confirmed present.
    import classify
    import report

    run_onboarding_or_confirm()

    print("\n  Classifying conversations...")
    classify.main()

    print("\n  Generating report...")
    report.main()

    print("\n  Opening your report...")
    open_report(REPORT_HTML)
    print("  Done. Your report is in the output/ folder.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted — this is resumable. Re-run to continue where you left off.\n")
        sys.exit(130)
