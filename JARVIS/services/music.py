import ctypes
import difflib
import re
import subprocess
import threading
import urllib.parse
import urllib.request
import webbrowser
import config

media_state = {
    "is_playing": False,
    "is_paused": False,
    "last_query": "",
    "last_video_id": "",
    "last_app": "youtube",
}

def fuzzy_score(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

def _fuzzy_word_match(word, targets, threshold=0.75):
    return any(fuzzy_score(word, t) >= threshold for t in targets)

def _youtube_key(key_char):
    ps = r"""
$shell = New-Object -ComObject WScript.Shell

$activated = $false
foreach ($title in @("YouTube","- Chrome","- Edge","- Firefox","- Brave","- Opera","- Chromium")) {
    try {
        if ($shell.AppActivate($title)) {
            $activated = $true
            Write-Host "M1:$title"
            break
        }
    } catch {}
}

if (-not $activated) {
    Add-Type @"
using System;using System.Runtime.InteropServices;
public class BW {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
}
"@
    foreach ($b in @("chrome","msedge","firefox","brave","chromium","opera")) {
        $procs = Get-Process -Name $b -ErrorAction SilentlyContinue |
                 Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero -and $_.MainWindowTitle -ne "" }
        if ($procs) {
            $hwnd = $procs[0].MainWindowHandle
            [BW]::ShowWindow($hwnd, 9)
            [BW]::BringWindowToTop($hwnd)
            [BW]::SetForegroundWindow($hwnd)
            $activated = $true
            Write-Host "M2:$($procs[0].ProcessName)"
            break
        }
    }
}

if (-not $activated) { Write-Host "FAIL"; exit }

Start-Sleep -Milliseconds 700
""" + f'$shell.SendKeys("{key_char}")\n' + r"""Write-Host "SENT"
"""
    try:
        result = subprocess.run(
            ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=5
        )
        out = result.stdout.strip()
        if "FAIL" in out or not out:
            ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xB3, 0, 2, 0)
    except Exception:
        ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0xB3, 0, 2, 0)

def _media_key_playpause():
    threading.Thread(target=lambda: _youtube_key("k"), daemon=True).start()

def _media_key_next():
    threading.Thread(target=lambda: _youtube_key("+N"), daemon=True).start()

def _media_key_prev():
    threading.Thread(target=lambda: _youtube_key("j"), daemon=True).start()

def _youtube_search_play(query):
    encoded = urllib.parse.quote(query)
    def _bg():
        try:
            req = urllib.request.Request(
                f"https://www.youtube.com/results?search_query={encoded}",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
            if ids:
                media_state["last_video_id"] = ids[0]
                webbrowser.open(f"https://www.youtube.com/watch?v={ids[0]}&autoplay=1")
            else:
                webbrowser.open(f"https://www.youtube.com/results?search_query={encoded}")
        except Exception:
            webbrowser.open(f"https://www.youtube.com/results?search_query={encoded}")
    threading.Thread(target=_bg, daemon=True).start()

def handle_play(t):
    global media_state
    words = t.split()

    FORCE_PHRASES = ["not playing", "didn't play", "did not play", "is not playing", "isn't playing", "force play", "not play", "does not play", "doesn't play", "still not playing", "still not play"]
    if any(p in t for p in FORCE_PHRASES):
        _media_key_playpause()
        media_state["is_playing"] = True; media_state["is_paused"] = False
        return f"Sorry about that. I just sent the playback signal again {config.YOUR_NAME}."

    PAUSE_EXACT = {"pause", "stop", "halt", "freeze"}
    PAUSE_FUZZY = ["pause", "paus", "pase", "stopp"]
    MEDIA_N = ["song", "video", "music", "audio", "track", "youtube", "vlc", "playing", "background"]

    has_med = any(n in t for n in MEDIA_N)
    is_command = len(words) <= 3

    pause_exact_hit = any(w in PAUSE_EXACT for w in words)
    pause_fuzzy_hit = any(_fuzzy_word_match(w, PAUSE_FUZZY, threshold=0.85) for w in words)
    pause_hit = pause_exact_hit or (pause_fuzzy_hit and has_med)

    question_words = {"what", "why", "how", "when", "where", "who", "which", "does", "is", "are", "can", "did", "do"}
    standby_words = {"talking", "voice", "jarvis", "sleep", "quiet", "up", "conversation"}
    has_question = any(w in question_words for w in words[:3])
    has_standby = any(w in standby_words for w in words)

    if pause_hit and (has_med or is_command) and not has_question and not has_standby:
        if media_state["is_paused"]:
            return f"It is already paused {config.YOUR_NAME}."
        _media_key_playpause()
        media_state["is_paused"] = True; media_state["is_playing"] = False
        q = media_state["last_query"]
        return f"Paused {q} {config.YOUR_NAME}." if q else f"Paused {config.YOUR_NAME}."

    NEXT_EXACT = {"next", "skip"}
    next_hit = any(w in NEXT_EXACT or _fuzzy_word_match(w, ["next", "skip", "forward"], 0.88) for w in words)
    if next_hit and (has_med or is_command) and not has_question:
        _media_key_next(); return f"Next track {config.YOUR_NAME}."

    PREV_EXACT = {"previous", "prev"}
    prev_hit = any(w in PREV_EXACT or _fuzzy_word_match(w, ["previous", "prev", "rewind"], 0.85) for w in words)
    if prev_hit and (has_med or is_command) and not has_question:
        _media_key_prev(); return f"Going back {config.YOUR_NAME}."

    RESUME_W = ["resume", "unpause", "continue"]
    is_resume_word = any(_fuzzy_word_match(w, RESUME_W) for w in words)
    is_resume_phrase = bool(re.match(
        r'^(play|resume|continue)\s*(the|it|that|this|back|again|same|music|song|video|track|now|please|on)?(\s+(song|video|music|track|again|please|back|now|same))?$',
        t.strip()))
    if (is_resume_word or is_resume_phrase) and not has_question:
        if media_state["is_playing"] and not media_state["is_paused"]:
            return f"It is already playing {config.YOUR_NAME}."
        elif media_state["is_paused"] or is_resume_word:
            _media_key_playpause()
            media_state["is_paused"] = False; media_state["is_playing"] = True
            q = media_state["last_query"]
            return f"Resuming {q} {config.YOUR_NAME}." if q else f"Resuming {config.YOUR_NAME}."

    SEARCH_GOOGLE_PHRASES = ["search google", "google search", "search on google", "search in google", "google for", "find on google"]
    WHATSAPP_PHRASES = ["whatsapp", "message to", "send message", "send hi", "send hello", "chat with", "open chat", "send to", "text to"]
    if any(p in t for p in SEARCH_GOOGLE_PHRASES) or any(p in t for p in WHATSAPP_PHRASES):
        return None

    PLAY_STARTERS = [
        "play ", "watch ", "find me ", "show me ", "put on ",
        "can you play", "i want to watch", "i want to see", "jarvis play",
        "ok jarvis play", "hey jarvis play", "please play", "please watch",
        "open youtube", "search youtube for", "look up ", "play me ",
        "play a ", "play some ", "watch a ", "watch some ", "watch the ",
    ]
    triggered = any(t.startswith(s) or s.strip() in t for s in PLAY_STARTERS)
    if not triggered and re.search(r'\b(play|watch)\b\s+\S+', t): triggered = True

    MEDIA_TRIGGER_WORDS = ["video", "videos", "song", "songs", "music", "album", "movie", "movies", "cartoon", "anime", "clip", "episode"]
    if not triggered and any(mw in words for mw in MEDIA_TRIGGER_WORDS):
        triggered = True

    if t.strip() in ["again", "play again", "again please"] or t.endswith(" again"):
        if media_state["is_paused"]:
            _media_key_playpause()
            media_state["is_paused"] = False; media_state["is_playing"] = True
            q = media_state["last_query"]
            return f"Resuming {q} {config.YOUR_NAME}." if q else f"Resuming {config.YOUR_NAME}."
        elif media_state["is_playing"]:
            return f"It is already playing {config.YOUR_NAME}."

    if triggered:
        q = re.sub(r'\b(play|watch|find|show|put|on|open|look|up|youtube|google|for|a|an|the|me|please|jarvis|ok|okay|hey|can|you|could|i|want|to)\b', '', t).strip()
        q = re.sub(r'\s+', ' ', q).strip()
        if not q: q = "trending music"
        media_state["last_query"] = q
        media_state["is_playing"] = True
        media_state["is_paused"] = False
        _youtube_search_play(q)
        return f"Playing {q} on YouTube {config.YOUR_NAME}."

    return None