import json
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

def ask(prompt, max_chars=None, options=None):
    while True:
        if options:
            print(f"\n{prompt}")
            for i, opt in enumerate(options, 1):
                print(f"  {i}. {opt}")
            choice = input("Enter number: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(options):
                return options[int(choice) - 1]
            print("  Please enter a valid number.")
        else:
            value = input(f"\n{prompt}: ").strip()
            if not value:
                print("  This field is required.")
                continue
            if max_chars and len(value) > max_chars:
                print(f"  Please keep it under {max_chars} characters (yours: {len(value)}).")
                continue
            return value

def run():
    print("\n" + "="*55)
    print("  claude-mirror — Personal AI Usage Analyser")
    print("  One-time setup. Takes under 2 minutes.")
    print("="*55)
    print("\nLet's personalise your report.\n")

    name = ask("Your name")
    mother_tongue = ask("Your mother tongue (e.g. Tamil, Hindi, Bengali)")
    profession = ask("Your profession in one line (max 60 characters)", max_chars=60)
    goal = ask("Your current top goal in one line (max 100 characters)", max_chars=100)
    period = ask(
        "Time period to analyse",
        options=[
            "Last 3 months",
            "Last 6 months",
            "Last 12 months",
            "All available data"
        ]
    )

    now = datetime.utcnow()
    if period == "Last 3 months":
        cutoff = now - relativedelta(months=3)
    elif period == "Last 6 months":
        cutoff = now - relativedelta(months=6)
    elif period == "Last 12 months":
        cutoff = now - relativedelta(months=12)
    else:
        cutoff = None

    config = {
        "name": name,
        "mother_tongue": mother_tongue,
        "profession": profession,
        "goal": goal,
        "period_label": period,
        "cutoff_date": cutoff.isoformat() if cutoff else None,
        "created_at": now.isoformat()
    }

    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

    print("\n" + "="*55)
    print(f"  Got it, {name}. Config saved.")
    print("="*55)
    print("\nNext step:")
    print("  python3 classify.py\n")

if __name__ == "__main__":
    run()
