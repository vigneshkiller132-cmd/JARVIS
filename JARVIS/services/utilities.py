import datetime
import json
import os
import re
import subprocess
import time
import config
from core.memory import memory, save_memory

command_log = []

def log_command(cmd, result):
    entry = {
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "command": cmd,
        "result": (result or "")[:80]
    }
    command_log.append(entry)
    try:
        existing = []
        if os.path.exists(config.LOG_FILE):
            with open(config.LOG_FILE, "r") as f: existing = json.load(f)
        existing.append(entry)
        with open(config.LOG_FILE, "w") as f: json.dump(existing[-500:], f, indent=2)
    except Exception: pass

def get_clipboard():
    try:
        res = subprocess.run(["powershell", "-Command", "Get-Clipboard"],
                             capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        text = res.stdout.strip()
        if text: return f"Clipboard contains: {text[:200]} {config.YOUR_NAME}."
        return f"Clipboard is empty {config.YOUR_NAME}."
    except Exception: return f"Could not read clipboard {config.YOUR_NAME}."

def set_clipboard(text):
    try:
        escaped = text.replace("'", "''")
        subprocess.run(["powershell", "-Command", f"Set-Clipboard -Value '{escaped}'"],
                       creationflags=subprocess.CREATE_NO_WINDOW)
        return f"Copied to clipboard {config.YOUR_NAME}."
    except Exception: return f"Could not copy {config.YOUR_NAME}."

def _escape_sendkeys(text):
    special = {'+': '{+}', '^': '{^}', '%': '{%}', '~': '{~}',
               '(': '{(}', ')': '{(}', '[': '{[}', ']': '{]}',
               '{': '{{', '}': '}}'}
    return ''.join(special.get(c, c) for c in text)

def type_text(text):
    m = re.search(r'(?:type|write|input)\s+(.+)', text)
    if not m: return f"What should I type {config.YOUR_NAME}?"
    to_type = m.group(1).strip()
    safe = _escape_sendkeys(to_type)
    ps = f"""
$shell = New-Object -ComObject WScript.Shell
$shell.SendKeys("{safe}")
"""
    try:
        time.sleep(0.5)
        subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", ps],
                       creationflags=subprocess.CREATE_NO_WINDOW, timeout=3)
        return f"Typed: {to_type} {config.YOUR_NAME}."
    except Exception: return f"Could not type that {config.YOUR_NAME}."

def save_note(text):
    m = re.search(r'(?:save note|note|remember)\s+(.+)', text)
    if not m: return f"What should I note down {config.YOUR_NAME}?"
    note = m.group(1).strip()
    key = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    if "notes" not in memory: memory["notes"] = {}
    memory["notes"][key] = note
    save_memory()
    return f"Note saved {config.YOUR_NAME}: {note}"

def read_notes():
    notes = memory.get("notes", {})
    if not notes: return f"No notes saved {config.YOUR_NAME}."
    recent = list(notes.items())[-3:]
    return f"Your last {len(recent)} notes {config.YOUR_NAME}: " + " | ".join(f"{k}: {v}" for k, v in recent)