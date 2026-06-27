import json
from pathlib import Path

COMMANDS_FILE = Path(__file__).parent.parent / 'data' / 'custom_commands.json'

def load_commands():
    try:
        if COMMANDS_FILE.exists():
            with open(COMMANDS_FILE, 'r') as f:
                return json.load(f).get('commands', [])
    except:
        pass
    return []

def save_commands(commands):
    COMMANDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(COMMANDS_FILE, 'w') as f:
        json.dump({'commands': commands}, f, indent=2, ensure_ascii=False)