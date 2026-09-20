import os
import psutil
import socket
import subprocess
import config

APP_CATEGORIES = {
    "Browsers": ["chrome.exe", "firefox.exe", "msedge.exe", "brave.exe", "opera.exe"],
    "Media": ["vlc.exe", "wmplayer.exe", "spotify.exe", "mpv.exe", "potplayer.exe"],
    "Productivity": ["winword.exe", "excel.exe", "powerpnt.exe", "onenote.exe", "outlook.exe", "notepad.exe"],
    "Dev Tools": ["code.exe", "pycharm64.exe", "devenv.exe", "sublime_text.exe", "notepad++.exe"],
    "Communication": ["teams.exe", "slack.exe", "discord.exe", "skype.exe", "zoom.exe", "telegram.exe"],
    "Gaming": ["steam.exe", "epicgameslauncher.exe", "leagueclient.exe", "battle.net.exe"],
    "Security": ["msmpeng.exe", "avgui.exe", "avp.exe", "bdagent.exe", "mbam.exe"],
    "System": ["explorer.exe", "svchost.exe", "taskmgr.exe", "cmd.exe", "powershell.exe"],
    "Utilities": ["7zfm.exe", "winrar.exe", "ccleaner.exe", "everything.exe", "sharex.exe"],
}

def get_all_drives():
    drives = []
    for p in psutil.disk_partitions():
        if os.path.exists(p.mountpoint): drives.append(p.mountpoint)
    return drives

def get_storage():
    lines = [f"Storage {config.YOUR_NAME}."]
    for p in psutil.disk_partitions():
        try:
            u = psutil.disk_usage(p.mountpoint)
            lines.append(f"Drive {p.mountpoint}: {round(u.used/(1024**3),1)} GB used of {round(u.total/(1024**3),1)} GB.")
        except Exception: pass
    return " ".join(lines)

def get_system_info():
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        b = psutil.sensors_battery()
        bat = f"{int(b.percent)}% {'charging' if b.power_plugged else 'discharging'}" if b else "N/A"
        wifi = "not detected"
        try:
            res = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True)
            for line in res.stdout.split("\n"):
                if "SSID" in line and "BSSID" not in line:
                    wifi = line.split(":")[1].strip(); break
        except Exception: pass
        return (f"System info {config.YOUR_NAME}. PC: {os.environ.get('COMPUTERNAME','?')}. "
                f"IP: {socket.gethostbyname(socket.gethostname())}. WiFi: {wifi}. "
                f"CPU: {cpu}%. RAM: {round(ram.used/(1024**3),1)} of {round(ram.total/(1024**3),1)} GB. "
                f"Battery: {bat}. {get_storage()}")
    except Exception: return f"Could not get system info {config.YOUR_NAME}."

def get_background_apps():
    try: procs = [p.name().lower() for p in psutil.process_iter(['name'])]
    except Exception: return f"Could not read processes {config.YOUR_NAME}."
    fc = {cat: [a for a in al if a in procs] for cat, al in APP_CATEGORIES.items()}
    fc = {k: v for k, v in fc.items() if v}
    all_e = list(set(p for p in procs if p.endswith(".exe")))
    lines = [f"There are {len(all_e)} processes {config.YOUR_NAME}."]
    for cat, apps in fc.items():
        lines.append(f"{cat}: {', '.join(a.replace('.exe','') for a in apps)}.")
    return " ".join(lines)