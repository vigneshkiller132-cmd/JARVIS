import datetime
import re
import threading
import time
import config
from core.memory import memory, save_memory

reminder_running = False
active_timers = []

def parse_time(text):
    m = re.search(r'in\s+(\d+)\s*(second|sec|minute|min|hour|hr)', text)
    if m:
        v = int(m.group(1))
        u = m.group(2)
        secs = v if 'sec' in u else v*60 if 'min' in u else v*3600
        return datetime.datetime.now() + datetime.timedelta(seconds=secs)
    m = re.search(r'at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text)
    if m:
        h = int(m.group(1))
        mins = int(m.group(2) or 0)
        ap = m.group(3)
        if ap == 'pm' and h != 12: h += 12
        if ap == 'am' and h == 12: h = 0
        t = datetime.datetime.now().replace(hour=h, minute=mins, second=0, microsecond=0)
        if t < datetime.datetime.now(): t += datetime.timedelta(days=1)
        return t
    return None

def add_reminder(text, speak_func):
    m = re.search(r'(?:remind me (?:at \S+ )?to |remind me in [^to]+ to )(.+)', text)
    msg = m.group(1).strip() if m else text
    rt = parse_time(text)
    if not rt:
        return f"Sorry {config.YOUR_NAME}, I could not understand the time."
    entry = {"time": rt.strftime("%Y-%m-%d %H:%M:%S"), "message": msg}
    if "reminders" not in memory: memory["reminders"] = []
    memory["reminders"].append(entry)
    save_memory()
    _start_reminder_loop(speak_func)
    return f"Reminder set {config.YOUR_NAME}. I will remind you to {msg} at {rt.strftime('%I:%M %p')}."

def set_timer(text, speak_func):
    m = re.search(r'(\d+)\s*(second|sec|minute|min|hour|hr)', text)
    if not m:
        return f"Sorry {config.YOUR_NAME}, I could not understand the duration."
    v = int(m.group(1))
    u = m.group(2)
    secs = v if 'sec' in u else v*60 if 'min' in u else v*3600
    unit_name = "seconds" if 'sec' in u else "minutes" if 'min' in u else "hours"
    def _fire():
        time.sleep(secs)
        speak_func(f"Timer done {config.YOUR_NAME}. Your {v} {unit_name} timer has ended.")
    t = threading.Thread(target=_fire, daemon=True)
    t.start()
    active_timers.append(t)
    return f"Timer set for {v} {unit_name} {config.YOUR_NAME}."

def _start_reminder_loop(speak_func):
    global reminder_running
    if not reminder_running:
        reminder_running = True
        threading.Thread(target=_reminder_loop, args=(speak_func,), daemon=True).start()

def _reminder_loop(speak_func):
    global reminder_running
    while True:
        time.sleep(20)
        now = datetime.datetime.now()
        due, remaining = [], []
        for r in memory.get("reminders", []):
            rt = datetime.datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S")
            (due if now >= rt else remaining).append(r)
        for r in due:
            speak_func(f"Reminder {config.YOUR_NAME}: {r['message']}")
        if due:
            memory["reminders"] = remaining
            save_memory()
        if not remaining:
            reminder_running = False
            break

def list_reminders():
    rem = memory.get("reminders", [])
    if not rem: return f"No reminders set {config.YOUR_NAME}."
    return f"You have {len(rem)} reminder(s) {config.YOUR_NAME}. " + " | ".join(f"{r['message']} at {r['time'][11:16]}" for r in rem)