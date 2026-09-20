import urllib.request
import urllib.parse
import config

def get_weather(city=""):
    try:
        c = city.strip() or config.DEFAULT_CITY
        url = f"https://wttr.in/{urllib.parse.quote(c)}?format=3"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return f"Weather: {r.read().decode('utf-8').strip()} {config.YOUR_NAME}."
    except Exception:
        return f"Could not fetch weather {config.YOUR_NAME}. Check your internet."