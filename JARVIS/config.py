import os
import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
YOUR_NAME = os.getenv("YOUR_NAME", "Boss")
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Tiruppur")
SPEECH_RATE = int(os.getenv("SPEECH_RATE", 1))
SPEECH_VOLUME = int(os.getenv("SPEECH_VOLUME", 100))
UNLOCK_PASSWORD = os.getenv("UNLOCK_PASSWORD", "9894")

USER = os.path.expanduser("~")
DESKTOP = os.path.join(USER, "Desktop")
TOP = USER

LEARN_FILE = os.path.join(USER, "jarvis_memory.json")
VOICE_FILE = os.path.join(USER, "jarvis_voice_profile.json")
LOG_FILE = os.path.join(USER, "jarvis_log.json")

WAKE_WORDS = [
    "hey jarvis", "hello jarvis", "hi jarvis", "okay jarvis",
    "ok jarvis", "jarvis", "hey j", "wake up jarvis",
]