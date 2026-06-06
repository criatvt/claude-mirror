#!/usr/bin/env python3
"""claude-mirror — single-command entrypoint.

Runs the full pipeline end-to-end:

    python3 claude_mirror.py

It performs friendly prerequisite checks, then calls onboarding.main(),
classify.main(), and report.main() in order. Each prereq failure produces an
actionable message rather than a stack trace.

Note: the three stage modules (onboarding/classify/report) are imported lazily
inside main(), *after* check_python_deps() runs — importing them eagerly would
pull in pandas/matplotlib/etc. and raise a raw ImportError before we can print a
friendly message.
"""
import json
import os
import sys
import urllib.request
import urllib.error

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, 'config.json')
DATA_PATH = os.path.join(BASE, 'data', 'conversations.json')

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


def check_conversations_present():
    # Smart input detection (auto-locating exports) arrives in #30; for now we
    # just verify the expected file is present.
    if not os.path.exists(DATA_PATH):
        _fail(
            "No conversation data found at data/conversations.json\n"
            "    Export your history and place conversations.json in the data/ folder."
        )


def main():
    print("\n  Claude Mirror — checking prerequisites...")
    check_python_deps()
    check_ollama_reachable()
    check_model_available(MODEL_NAME)
    check_conversations_present()
    print("  ✓ All prerequisites met.")

    # Safe to import the heavy stages now that deps are confirmed present.
    import onboarding
    import classify
    import report

    # Onboarding always prompts today; skip it when a config already exists so
    # re-runs don't re-ask. The fuller smart/inline onboarding flow lands in #30.
    if os.path.exists(CONFIG_PATH):
        print("\n  Using existing config.json (run onboarding.py to change it).")
    else:
        print("\n  Running onboarding...")
        onboarding.main()

    print("\n  Classifying conversations...")
    classify.main()

    print("\n  Generating report...")
    report.main()

    # Auto-opening the report cross-platform is handled in #31.
    print("\n  Done. Your report is in the output/ folder.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted — this is resumable. Re-run to continue where you left off.\n")
        sys.exit(130)
