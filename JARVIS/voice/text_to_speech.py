import re
import subprocess
import threading
import time
import speech_recognition as sr
import config
from voice.authentication import verify_voice

speaking = False
speak_proc = None

def clean_for_speech(text):
    text = re.sub(r'```[\s\S]*?```', ' code block. ', text)
    text = re.sub(r'`[^`]*`', '', text)
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'#{1,6}\s?', '', text)
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r"[\"'`\\<>&|\u2014\u2013\u2018\u2019\u201c\u201d]", '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def stop_speaking():
    global speaking, speak_proc
    speaking = False
    if speak_proc and speak_proc.poll() is None:
        try:
            speak_proc.kill()
        except Exception:
            pass
    speak_proc = None

def speak(text, add_msg_callback=None, status_callback=None, process_input_callback=None, voice_state=None):
    global speaking, speak_proc
    speaking = True
    print(f"\n🤖 Jarvis: {text}")
    if add_msg_callback:
        add_msg_callback("Jarvis", text)
    if status_callback:
        status_callback("🔊 Speaking...")
    clean = clean_for_speech(text)
    if not clean:
        speaking = False
        return
    
    clean = clean.replace("'", " ").replace('"', ' ').replace('`', ' ').replace('\n', ' ')
    interrupted = [None]

    def _interrupt():
        try:
            time.sleep(0.5)
            if not speaking: return
            r = sr.Recognizer()
            r.dynamic_energy_threshold = False
            with sr.Microphone() as src:
                r.adjust_for_ambient_noise(src, duration=1.5)
                r.energy_threshold = max(r.energy_threshold * 1.5, 800)
                print(f"  [interrupt] threshold set to {r.energy_threshold:.0f}")
                while speaking:
                    try:
                        audio = r.listen(src, timeout=1, phrase_time_limit=4)
                        if not speaking: break
                        if not verify_voice(audio): continue
                        stop_speaking()
                        if status_callback: status_callback("🎤 Listening...")
                        time.sleep(0.4)
                        r2 = sr.Recognizer()
                        r2.energy_threshold = 300
                        r2.dynamic_energy_threshold = True
                        with sr.Microphone() as src2:
                            r2.adjust_for_ambient_noise(src2, duration=0.3)
                            try:
                                audio2 = r2.listen(src2, timeout=6, phrase_time_limit=12)
                                txt = r2.recognize_google(audio2, language="en-IN").strip()
                                interrupted[0] = txt if txt else ""
                            except Exception:
                                interrupted[0] = ""
                        break
                    except sr.WaitTimeoutError: continue
                    except Exception: break
        except Exception: pass

    threading.Thread(target=_interrupt, daemon=True).start()

    ps = (f"Add-Type -AssemblyName System.Speech; "
          f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          f"$s.Rate = {config.SPEECH_RATE};$s.Volume = {config.SPEECH_VOLUME}; "
          f"$s.Speak('{clean}');")
    try:
        speak_proc = subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-Command", ps],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        speak_proc.wait()
    except Exception as e:
        print(f"  (speech error: {e})")

    speaking = False
    speak_proc = None

    if interrupted[0] and process_input_callback:
        txt = interrupted[0]
        if add_msg_callback: add_msg_callback("You", txt)
        threading.Thread(target=process_input_callback, args=(txt,), daemon=True).start()
    elif voice_state and (voice_state.get("voice_mode") or voice_state.get("awake")):
        if status_callback: status_callback("🎤 Listening...")
        if voice_state.get("auto_listen_func"):
            threading.Thread(target=voice_state["auto_listen_func"], daemon=True).start()