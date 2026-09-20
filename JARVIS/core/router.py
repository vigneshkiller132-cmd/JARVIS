import config
from core.ai import ask
from core.agent import is_agent_task, run_agent
from services.calculator import calculate, unit_convert
from services.clipboard import get_clipboard, set_clipboard
from services.music import handle_play
from services.news import get_news
from services.reminders import add_reminder, set_timer, list_reminders
from services.utilities import log_command, type_text, save_note, read_notes
from services.weather import get_weather
from system.automation import handle_app, handle_website, handle_folder, handle_system

def process_input(text, status_cb, add_msg_cb, speak_cb):
    t = text.lower().strip()
    if not t: return

    # Check Agentic Execution
    if is_agent_task(t):
        res = run_agent(text, status_cb, add_msg_cb, speak_cb)
        log_command(text, res)
        speak_cb(res)
        return

    # Direct System/Service Commands
    res = (handle_play(t) or
           handle_folder(t) or
           handle_website(t) or
           handle_app(t) or
           handle_system(t, speak_func=speak_cb))

    if not res:
        if "weather" in t: res = get_weather()
        elif "news" in t: res = get_news()
        elif "remind" in t: res = add_reminder(t, speak_cb)
        elif "timer" in t: res = set_timer(t, speak_cb)
        elif "notes" in t or "note" in t: res = read_notes() if "read" in t else save_note(t)
        elif "type" in t or "write" in t: res = type_text(t)
        elif "clipboard" in t: res = get_clipboard()
        elif "convert" in t: res = unit_convert(t)
        elif "calculate" in t or "what is" in t: res = calculate(t)

    if res:
        log_command(text, res)
        speak_cb(res)
        return

    # Fallback to AI Ask
    reply = ask(text)
    log_command(text, reply)
    speak_cb(reply)