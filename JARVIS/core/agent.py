import datetime
import json
import re
import subprocess
import urllib.parse
import urllib.request
import config
from core.ai import client
from core.memory import memory, save_memory
from services.weather import get_weather
from services.calculator import calculate
from services.music import _youtube_search_play, media_state
from system.system_info import get_system_info
from system.automation import handle_app, handle_website, handle_folder, handle_system

AGENT_TOOLS = [
    {"type": "function", "function": {"name": "search_web", "description": "Search Google", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "open_app", "description": "Open app/web/folder", "parameters": {"type": "object", "properties": {"target": {"type": "string"}}, "required": ["target"]}}},
    {"type": "function", "function": {"name": "save_note", "description": "Save note", "parameters": {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]}}},
    {"type": "function", "function": {"name": "task_complete", "description": "Finish task", "parameters": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}}},
]

def is_agent_task(text):
    t = text.lower().strip()
    TRIGGERS = ["do the following", "do this for me", "complete this task", "i need you to", "step by step", "automatically", "agent mode"]
    if any(tr in t for tr in TRIGGERS): return True
    has_and = " and " in t or " then " in t
    words = set(t.split())
    actions = words & {"open", "search", "play", "find", "save", "type", "calculate"}
    return has_and and len(actions) >= 2

def _agent_execute_tool(tool_name, tool_args, speak_func):
    try:
        if tool_name == "search_web":
            q = tool_args.get("query", "")
            return f"Searched for {q}"
        elif tool_name == "save_note":
            c = tool_args.get("content", "")
            if "notes" not in memory: memory["notes"] = {}
            memory["notes"][datetime.datetime.now().strftime("%Y-%m-%d %H:%M")] = c
            save_memory()
            return f"Note saved: {c}"
        elif tool_name == "task_complete":
            return "TASK_COMPLETE:" + tool_args.get("summary", "Task done.")
        return f"Tool executed: {tool_name}"
    except Exception as e:
        return f"Tool error: {e}"

def run_agent(task, status_cb, add_msg_cb, speak_cb):
    status_cb("🤖 Agent: Planning...")
    add_msg_cb("Jarvis", f"🤖 Starting agent task: {task}")
    date_str = datetime.datetime.now().strftime("%A, %B %d, %Y - %I:%M %p")
    messages = [
        {"role": "system", "content": f"You are JARVIS serving {config.YOUR_NAME}. TODAY: {date_str}"},
        {"role": "user", "content": f"Task: {task}"}
    ]
    step = 0
    final = None
    while step < 8:
        step += 1
        status_cb(f"🤖 Agent step {step}/8...")
        try:
            res = client.chat.completions.create(
                model="openai/gpt-oss-120b", messages=messages, tools=AGENT_TOOLS, tool_choice="auto", max_tokens=512, temperature=0.3
            )
        except Exception as e: return f"Agent error {config.YOUR_NAME}: {e}"
        msg = res.choices[0].message
        if not msg.tool_calls:
            final = msg.content or "Task complete."
            break
        for tc in msg.tool_calls:
            try: tool_args = json.loads(tc.function.arguments)
            except Exception: tool_args = {}
            res_str = _agent_execute_tool(tc.function.name, tool_args, speak_cb)
            if res_str.startswith("TASK_COMPLETE:"):
                final = res_str.replace("TASK_COMPLETE:", "").strip()
                break
        if final is not None: break
    status_cb("💤 Standby")
    return f"Task done {config.YOUR_NAME}. {final}"