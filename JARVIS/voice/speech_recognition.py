import time
import threading
import speech_recognition as sr
import config
from voice.authentication import verify_voice
import voice.text_to_speech as tts

listening = False
wake_active = True
awake = False
voice_mode = False

def wake_word_listener(status_cb, wake_label_cb, speak_cb):
    global awake
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True
    print("👂 Wake word listener active")
    while wake_active:
        try:
            with sr.Microphone() as src:
                r.adjust_for_ambient_noise(src, duration=0.5)
                while wake_active:
                    try:
                        audio = r.listen(src, timeout=2, phrase_time_limit=4)
                        text = r.recognize_google(audio, language="en-IN").lower().strip()
                        if any(w in text for w in config.WAKE_WORDS):
                            if not tts.speaking and not awake:
                                if verify_voice(audio):
                                    awake = True
                                    wake_label_cb("👂 AWAKE", "#00ff88")
                                    status_cb("👂 Listening...")
                                    threading.Thread(target=lambda: speak_cb(f"Yes {config.YOUR_NAME}?"), daemon=True).start()
                                else:
                                    status_cb("🔐 Access denied")
                                    ps = ("Add-Type -AssemblyName System.Speech;"
                                          "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                                          "$s.Rate=0;$s.Volume=100;"
                                          "$s.Speak('Access denied.');")
                                    subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-Command", ps],
                                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                                     creationflags=subprocess.CREATE_NO_WINDOW)
                    except sr.WaitTimeoutError: continue
                    except sr.UnknownValueError: continue
                    except Exception: time.sleep(0.5); break
        except Exception: time.sleep(2)

def auto_listen(status_cb, wake_label_cb, add_msg_cb, process_input_cb, speak_cb):
    global listening, awake
    if listening: return
    listening = True
    status_cb("🎤 Listening...")
    try:
        r = sr.Recognizer()
        r.pause_threshold = 0.8
        r.dynamic_energy_threshold = True
        with sr.Microphone() as src:
            r.adjust_for_ambient_noise(src, duration=0.5)
            if r.energy_threshold < 150:
                r.energy_threshold = 150
            try:
                audio = r.listen(src, timeout=10, phrase_time_limit=15)
                if not verify_voice(audio):
                    status_cb("🔐 Access denied")
                    speak_cb("Access denied.")
                    listening = False
                    return
                text = r.recognize_google(audio, language="en-IN")
                add_msg_cb("You", text)
                status_cb("🤖 Thinking...")
                threading.Thread(target=process_input_cb, args=(text,), daemon=True).start()
            except sr.WaitTimeoutError:
                awake = False
                wake_label_cb("💤 Standby", "#555555")
                status_cb("💤 Standby — say Hey Jarvis")
                if voice_mode:
                    time.sleep(0.3)
                    threading.Thread(target=auto_listen, args=(status_cb, wake_label_cb, add_msg_cb, process_input_cb, speak_cb), daemon=True).start()
            except sr.UnknownValueError:
                if voice_mode or awake:
                    status_cb("🎤 Listening...")
                    time.sleep(0.3)
                    threading.Thread(target=auto_listen, args=(status_cb, wake_label_cb, add_msg_cb, process_input_cb, speak_cb), daemon=True).start()
            except Exception as e:
                status_cb(f"Mic error: {e}")
    except Exception as e:
        status_cb(f"Mic error: {e}")
    finally:
        listening = False

def on_mic_click(mic_btn_cb, status_cb, wake_label_cb, add_msg_cb, process_input_cb, speak_cb):
    global voice_mode
    if voice_mode:
        voice_mode = False
        tts.stop_speaking()
        mic_btn_cb("🎤 Voice", "#1a1a2e")
        status_cb("💤 Standby")
    else:
        voice_mode = True
        mic_btn_cb("🔴 ON", "#ff4444")
        threading.Thread(target=auto_listen, args=(status_cb, wake_label_cb, add_msg_cb, process_input_cb, speak_cb), daemon=True).start()