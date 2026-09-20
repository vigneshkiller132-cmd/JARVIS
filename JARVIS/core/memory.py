import json
import os
import re
import datetime
import typing
import config

def load_memory() -> typing.Any:
    try:
        if os.path.exists(config.LEARN_FILE):
            with open(config.LEARN_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "command_frequency": {}, "favorite_apps": {}, "favorite_sites": {},
        "custom_shortcuts": {}, "topics_discussed": {}, "reminders": [],
        "notes": {}, "session_count": 0, "total_commands": 0, "last_seen": ""
    }

memory = load_memory()
memory["session_count"] = memory.get("session_count", 0) + 1
memory["last_seen"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

def save_memory():
    try:
        tmp = config.LEARN_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(memory, f, indent=2)
        os.replace(tmp, config.LEARN_FILE)
    except Exception:
        pass

save_memory()

def learn_command(ctype, value):
    key = f"{ctype}:{value}"
    memory["command_frequency"][key] = memory["command_frequency"].get(key, 0) + 1
    memory["total_commands"] = memory.get("total_commands", 0) + 1
    if ctype == "app":
        memory["favorite_apps"][value] = memory["favorite_apps"].get(value, 0) + 1
    elif ctype == "site":
        memory["favorite_sites"][value] = memory["favorite_sites"].get(value, 0) + 1
    save_memory()

def learn_topic(text):
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    stops = {"what", "this", "that", "with", "have", "from", "they", "will", "been", "when", "your",
             "jarvis", "boss", "about", "just", "some", "more", "also", "then", "than", "play", "open"}
    for w in words:
        if w not in stops:
            memory["topics_discussed"][w] = memory["topics_discussed"].get(w, 0) + 1
    save_memory()

def get_top(d, n=3):
    return sorted(d.items(), key=lambda x: x[1], reverse=True)[:n] if d else []

def personalized_context():
    ctx = []
    ta = get_top(memory.get("favorite_apps", {}), 3)
    ts = get_top(memory.get("favorite_sites", {}), 3)
    tt = get_top(memory.get("topics_discussed", {}), 5)
    if ta: ctx.append(f"Boss frequently uses: {', '.join([a[0] for a in ta])}.")
    if ts: ctx.append(f"Boss often visits: {', '.join([s[0] for s in ts])}.")
    if tt: ctx.append(f"Boss is interested in: {', '.join([t[0] for t in tt])}.")
    s = memory.get("session_count", 0)
    if s > 1: ctx.append(f"This is session {s} with Boss.")
    return " ".join(ctx)

def learn_shortcut(trigger, action):
    memory["custom_shortcuts"][trigger.lower()] = action
    save_memory()

def check_shortcut(text):
    for trigger, action in memory.get("custom_shortcuts", {}).items():
        if trigger in text.lower():
            return action
    return None

def get_learning_stats():
    ta = get_top(memory.get("favorite_apps", {}), 3)
    ts = get_top(memory.get("favorite_sites", {}), 3)
    tt = get_top(memory.get("topics_discussed", {}), 5)
    lines = [f"Learning report {config.YOUR_NAME}. {memory.get('session_count',0)} sessions. {memory.get('total_commands',0)} commands."]
    if ta: lines.append(f"Favourite apps: {', '.join([a[0] for a in ta])}.")
    if ts: lines.append(f"Favourite sites: {', '.join([s[0] for s in ts])}.")
    if tt: lines.append(f"Top topics: {', '.join([t[0] for t in tt])}.")
    sc = len(memory.get("custom_shortcuts", {}))
    if sc: lines.append(f"Learned {sc} custom shortcuts.")
    return " ".join(lines)