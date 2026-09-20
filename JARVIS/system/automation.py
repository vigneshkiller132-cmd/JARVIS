import ctypes
import difflib
import os
import re
import socket
import subprocess
import sys
import threading
import time
import webbrowser
import winreg
import psutil

import config
from core.memory import learn_command, get_learning_stats
from system.system_info import get_all_drives, get_storage, get_system_info, get_background_apps
from system.window_controls import minimize_all, restore_all

FOLDERS = {
    "downloads": os.path.join(config.USER, "Downloads"), "download": os.path.join(config.USER, "Downloads"),
    "desktop": config.DESKTOP, "documents": os.path.join(config.USER, "Documents"),
    "document": os.path.join(config.USER, "Documents"), "pictures": os.path.join(config.USER, "Pictures"),
    "photos": os.path.join(config.USER, "Pictures"), "music": os.path.join(config.USER, "Music"),
    "videos": os.path.join(config.USER, "Videos"), "onedrive": os.path.join(config.USER, "OneDrive"),
    "appdata": os.path.join(config.USER, "AppData"), "temp": os.path.join(config.USER, "AppData", "Local", "Temp"),
    "recycle bin": "shell:RecycleBinFolder", "trash": "shell:RecycleBinFolder",
    "this pc": "shell:MyComputerFolder", "my computer": "shell:MyComputerFolder",
    "program files": "C:\\Program Files", "windows": "C:\\Windows",
    "system32": "C:\\Windows\\System32",
    "c drive": "C:\\", "d drive": "D:\\", "e drive": "E:\\", "f drive": "F:\\",
    "home": config.USER,
}

SITES = {
    "youtube": "https://youtube.com", "whatsapp": "https://web.whatsapp.com",
    "gmail": "https://mail.google.com", "email": "https://mail.google.com",
    "github": "https://github.com", "twitter": "https://x.com",
    "facebook": "https://facebook.com", "instagram": "https://instagram.com",
    "insta": "https://instagram.com", "netflix": "https://netflix.com",
    "spotify": "https://open.spotify.com", "chatgpt": "https://chat.openai.com",
    "linkedin": "https://linkedin.com", "reddit": "https://reddit.com",
    "amazon": "https://amazon.com", "wikipedia": "https://wikipedia.org",
    "maps": "https://maps.google.com", "translate": "https://translate.google.com",
    "drive": "https://drive.google.com", "meet": "https://meet.google.com",
    "zoom": "https://zoom.us", "claude": "https://claude.ai",
    "stackoverflow": "https://stackoverflow.com", "twitch": "https://twitch.tv",
    "pinterest": "https://pinterest.com", "tiktok": "https://tiktok.com",
    "notion": "https://notion.so", "figma": "https://figma.com", "canva": "https://canva.com",
}

APPS = {
    "notepad": "notepad.exe", "calculator": "calc.exe", "calc": "calc.exe",
    "paint": "mspaint.exe", "task manager": "taskmgr.exe", "cmd": "cmd.exe",
    "command prompt": "cmd.exe", "powershell": "powershell.exe",
    "registry": "regedit.exe", "control panel": "control.exe",
    "snipping tool": "snippingtool.exe", "wordpad": "wordpad.exe",
    "magnifier": "magnify.exe", "resource monitor": "resmon.exe",
    "disk cleanup": "cleanmgr.exe", "file explorer": "explorer.exe",
    "character map": "charmap.exe", "system configuration": "msconfig.exe",
    "event viewer": "eventvwr.exe", "device manager": "devmgmt.msc",
    "disk management": "diskmgmt.msc", "services": "services.msc",
}

SHELL_APPS = {
    "settings": "ms-settings:", "camera": "microsoft.windows.camera:",
    "store": "ms-windows-store:", "photos app": "ms-photos:",
    "weather app": "bingweather:", "clock": "ms-clock:", "calendar": "outlookcal:",
    "mail app": "outlookmail:", "xbox": "xbox:", "movies": "mswindowsvideo:", "alarm": "ms-clock:",
}

CMD_APPS = {
    "visual studio code": "code", "vs code": "code", "vscode": "code",
    "visual studio": "devenv", "word": "winword", "excel": "excel",
    "powerpoint": "powerpnt", "outlook": "outlook", "teams": "teams",
    "skype": "skype", "vlc": "vlc", "discord": "discord", "steam": "steam",
    "spotify app": "spotify", "zoom app": "zoom", "telegram": "telegram",
    "obs": "obs64", "blender": "blender", "figma": "figma", "postman": "postman",
    "android studio": "studio64", "pycharm": "pycharm64", "intellij": "idea64",
    "gimp": "gimp-2.10", "7zip": "7zfm", "winrar": "winrar", "slack": "slack",
    "notion": "notion", "audacity": "audacity", "krita": "krita",
}

APP_FULL_PATHS = {
    "code": [
        os.path.join(config.USER, r"AppData\Local\Programs\Microsoft VS Code\Code.exe"),
        r"C:\Program Files\Microsoft VS Code\Code.exe",
        r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
    ],
    "winword": [
        r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
        r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
    ],
    "excel": [
        r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    ],
    "spotify": [
        os.path.join(config.USER, r"AppData\Roaming\Spotify\Spotify.exe"),
    ],
}

def fuzzy_score(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

def fuzzy_best(query, candidates, threshold=0.6):
    best_s, best_c = 0, None
    for c in candidates:
        s = fuzzy_score(query, c)
        if s > best_s: best_s, best_c = s, c
    return (best_c, best_s) if best_s >= threshold else (None, 0)

def extract_target(t):
    clean = t
    for p in ["open", "launch", "start", "run", "execute", "show me", "take me to", "go to",
              "navigate to", "find", "search for", "locate"]:
        if clean.startswith(p+" "): clean = clean[len(p):].strip(); break
    for w in [" the ", " a ", " an ", " my ", " please ", " jarvis ", " folder", " file", " app"]:
        clean = clean.replace(w, " ")
    return clean.strip()

def find_folder_fuzzy(query, max_depth=4):
    query = query.lower().strip()
    if not query or len(query) < 2: return None, None
    candidates = []
    roots = get_all_drives() + [config.TOP, os.path.join(config.USER, "Documents"), os.path.join(config.USER, "Downloads")]
    skip = {'windows', 'system32', 'syswow64', 'winsxs', '$recycle.bin', 'system volume information'}
    for root_path in roots:
        if not os.path.exists(root_path): continue
        try:
            for dp, dn, _ in os.walk(root_path):
                depth = dp.replace(root_path, "").count(os.sep)
                if depth > max_depth: dn.clear(); continue
                dn[:] = [d for d in dn if d.lower() not in skip and not d.startswith('.')]
                for d in dn:
                    s = fuzzy_score(query, d.lower())
                    if s >= 0.5: candidates.append((s, d, os.path.join(dp, d)))
        except Exception: continue
    if not candidates: return None, None
    candidates.sort(reverse=True)
    s, name, path = candidates[0]
    return (name, path) if s >= 0.55 else (None, None)

def find_app_on_pc(app_name):
    name = app_name.lower().strip()
    if not name or len(name) < 2: return None
    for rp in [r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
               r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths"]:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rp)
            for i in range(winreg.QueryInfoKey(key)[0]):
                sn = winreg.EnumKey(key, i)
                if fuzzy_score(name, sn.lower().replace(".exe", "")) >= 0.6 or name in sn.lower():
                    try:
                        sk = winreg.OpenKey(key, sn)
                        path = winreg.QueryValue(sk, None)
                        if path and os.path.exists(path): return path
                    except Exception: pass
        except Exception: pass
    return None

def handle_folder(t):
    if "close" in t and any(f in t for f in list(FOLDERS.keys())+["folder", "window", "explorer"]):
        os.system("taskkill /f /im explorer.exe >nul 2>&1")
        time.sleep(1); subprocess.Popen("explorer.exe")
        return f"Folders closed {config.YOUR_NAME}."
    if "close" in t or "kill" in t:
        return None
    for name, path in FOLDERS.items():
        if name in t:
            learn_command("folder", name)
            if path.startswith("shell:"): subprocess.Popen(f'explorer {path}')
            elif os.path.exists(path): subprocess.Popen(f'explorer "{path}"')
            else: return f"Could not find {name} {config.YOUR_NAME}."
            return f"Opening {name} {config.YOUR_NAME}."
    dm = re.search(r'\b([a-zA-Z])\s+(?:drive|disk|volume)\b', t)
    if dm:
        letter = dm.group(1).upper()
        dp = f"{letter}:\\"
        if os.path.exists(dp):
            subprocess.Popen(f'explorer "{dp}"')
            return f"Opening {letter} drive {config.YOUR_NAME}."
    fn = extract_target(t)
    if fn and len(fn) >= 2:
        fname, fpath = find_folder_fuzzy(fn)
        if fpath:
            subprocess.Popen(f'explorer "{fpath}"')
            learn_command("folder", fn)
            return f"Opening {fname} {config.YOUR_NAME}."
    return None

def _open_url(url):
    try:
        ret = ctypes.windll.shell32.ShellExecuteW(None, "open", url, None, None, 1)
        if ret > 32: return
    except Exception: pass
    webbrowser.open(url)

def handle_website(t):
    import urllib.parse
    if "google" in t:
        if any(w in t for w in ["search", "for", "about", "find"]):
            q = re.sub(r'\b(search|google|for|about|find|open|please|jarvis)\b', '', t).strip()
            q = re.sub(r'\s+', ' ', q).strip()
            _open_url(f"https://www.google.com/search?q={urllib.parse.quote(q)}")
            learn_command("site", "google")
            return f"Searching Google for {q} {config.YOUR_NAME}."
        _open_url("https://google.com"); learn_command("site", "google")
        return f"Opening Google {config.YOUR_NAME}."
    if "youtube" in t:
        q = re.sub(r'\b(open|youtube|search|play|watch|for|please|jarvis)\b', '', t).strip()
        if q:
            _open_url(f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}")
            return f"Searching YouTube for {q} {config.YOUR_NAME}."
        _open_url("https://youtube.com")
        return f"Opening YouTube {config.YOUR_NAME}."
    words = re.findall(r'\b\w+\b', t)
    for name, url in SITES.items():
        if all(x in words for x in name.split()) or fuzzy_score(t, name) >= 0.7:
            learn_command("site", name); _open_url(url)
            return f"Opening {name} {config.YOUR_NAME}."
    return None

def _find_app_full_path(cmd_name):
    paths = APP_FULL_PATHS.get(cmd_name.lower(), [])
    for p in paths:
        if '*' in p:
            import glob
            matches = glob.glob(p)
            if matches: return matches[0]
        elif os.path.exists(p):
            return p
    return None

def _launch(cmd):
    cmd_str = str(cmd).strip()
    if os.path.exists(cmd_str):
        try:
            subprocess.Popen([cmd_str], creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except Exception:
            ctypes.windll.shell32.ShellExecuteW(None, "open", cmd_str, None, None, 1)
            return True
    if re.match(r'^[a-zA-Z][a-zA-Z0-9+\-.]*:', cmd_str) and not cmd_str.endswith('.exe'):
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "open", cmd_str, None, None, 1)
            return True
        except Exception: pass
    try:
        subprocess.Popen(["cmd", "/c", "start", "", cmd_str], creationflags=subprocess.CREATE_NO_WINDOW)
        return True
    except Exception: pass
    return False

def _find_browser_path(browser_id):
    name = browser_id.lower()
    known = {
        "chrome": [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"],
        "msedge": [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"],
        "firefox": [r"C:\Program Files\Mozilla Firefox\firefox.exe"],
    }
    for p in known.get(name, []):
        if os.path.exists(p): return p
    return None

def handle_app(t):
    SPOTIFY_VARIANTS = ["spotif", "spodif", "spodify", "spotife", "spodife", "spotify"]
    if any(w in t for w in ["open ", "launch ", "start "]) and any(v in t for v in SPOTIFY_VARIANTS):
        subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", 'Start-Process "spotify:"'], creationflags=subprocess.CREATE_NO_WINDOW)
        return f"Opening Spotify {config.YOUR_NAME}."

    if "close" in t or "kill" in t:
        an = re.sub(r'\b(close|kill|the|a|an|please|jarvis)\b', '', t).strip()
        CLOSE_MAP = {
            "chrome": "chrome.exe", "firefox": "firefox.exe", "edge": "msedge.exe",
            "notepad": "notepad.exe", "vscode": "Code.exe", "code": "Code.exe",
        }
        if any(v in an for v in SPOTIFY_VARIANTS):
            subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", "Stop-Process -Name Spotify -Force -ErrorAction SilentlyContinue"], creationflags=subprocess.CREATE_NO_WINDOW)
            return f"Closed Spotify {config.YOUR_NAME}."
        if an:
            exe = CLOSE_MAP.get(an, an.split()[0] + ".exe")
            proc_name = exe.replace(".exe", "").replace(".EXE", "")
            subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", f"Stop-Process -Name {proc_name} -Force -ErrorAction SilentlyContinue"], creationflags=subprocess.CREATE_NO_WINDOW)
            return f"Closed {an} {config.YOUR_NAME}."

    for name, exe in APPS.items():
        if name in t:
            learn_command("app", name); _launch(exe)
            return f"Opening {name} {config.YOUR_NAME}."
    for name, uri in SHELL_APPS.items():
        if name in t:
            learn_command("app", name); _launch(uri)
            return f"Opening {name} {config.YOUR_NAME}."
    for name, cmd in CMD_APPS.items():
        if name in t:
            learn_command("app", name)
            full_path = _find_app_full_path(cmd)
            if full_path: subprocess.Popen([full_path], creationflags=subprocess.CREATE_NO_WINDOW)
            else: _launch(cmd)
            return f"Opening {name} {config.YOUR_NAME}."
    return None

def handle_system(t, speak_func=None):
    if any(w in t for w in ["system info", "pc info", "pc status"]):
        return get_system_info()
    if any(w in t for w in ["storage", "disk usage"]):
        return get_storage()
    if any(w in t for w in ["learning stats", "my habits", "learning report"]):
        return get_learning_stats()
    if any(w in t for w in ["show desktop", "minimize all"]):
        minimize_all(); return f"Showing desktop {config.YOUR_NAME}."
    if any(w in t for w in ["restore all", "show all windows"]):
        restore_all(); return f"All windows restored {config.YOUR_NAME}."
    if any(w in t for w in ["background apps", "running apps"]):
        return get_background_apps()
    if any(w in t for w in ["shut down", "shutdown"]):
        if speak_func: speak_func(f"Shutting down {config.YOUR_NAME}.")
        subprocess.Popen(["shutdown", "/s", "/t", "5"]); sys.exit(0)
    if any(w in t for w in ["restart", "reboot"]):
        if speak_func: speak_func(f"Restarting {config.YOUR_NAME}.")
        subprocess.Popen(["shutdown", "/r", "/t", "5"]); sys.exit(0)
    if "lock" in t and "unlock" not in t:
        ctypes.windll.user32.LockWorkStation(); return f"Screen locked {config.YOUR_NAME}."
    if any(w in t for w in ["unlock screen", "unlock computer", "unlock pc"]):
        def _do_unlock():
            pwd = config.UNLOCK_PASSWORD
            ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0)
            time.sleep(1.2)
            ps = f'$shell = New-Object -ComObject WScript.Shell; $shell.SendKeys("{pwd}"); Start-Sleep -Milliseconds 400; $shell.SendKeys("{{ENTER}}")'
            subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", ps], creationflags=subprocess.CREATE_NO_WINDOW, timeout=6)
        threading.Thread(target=_do_unlock, daemon=True).start()
        return f"Unlocking screen {config.YOUR_NAME}."
    return None