import threading
import tkinter as tk
from tkinter import scrolledtext
import config
import voice.speech_recognition as sr_module
from voice.authentication import load_voice_profile, enroll_voice, reset_voice_profile
from voice.text_to_speech import speak
from core.router import process_input

class JARVISGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("JARVIS AI Assistant")
        self.root.geometry("750x550")
        self.root.configure(bg="#0f0f1b")

        # Top Bar
        top_frame = tk.Frame(root, bg="#1a1a2e", height=40)
        top_frame.pack(fill="x", side="top")
        
        self.auth_label = tk.Label(top_frame, text="🔓 Voice Auth: OFF", fg="#ff4444", bg="#1a1a2e", font=("Segoe UI", 10, "bold"))
        self.auth_label.pack(side="left", padx=10)

        self.wake_label = tk.Label(top_frame, text="💤 Standby", fg="#555555", bg="#1a1a2e", font=("Segoe UI", 10, "bold"))
        self.wake_label.pack(side="right", padx=10)

        # Log Display
        self.chat_log = scrolledtext.ScrolledText(root, bg="#161625", fg="#ffffff", font=("Segoe UI", 10), wrap="word")
        self.chat_log.pack(fill="both", expand=True, padx=10, pady=10)

        # Status Bar
        self.status_label = tk.Label(root, text="System Ready", fg="#00ff88", bg="#0f0f1b", font=("Segoe UI", 9))
        self.status_label.pack(side="top", anchor="w", padx=10)

        # Bottom Input Area
        input_frame = tk.Frame(root, bg="#0f0f1b")
        input_frame.pack(fill="x", side="bottom", padx=10, pady=10)

        self.entry = tk.Entry(input_frame, bg="#1a1a2e", fg="#ffffff", font=("Segoe UI", 11), insertbackground="white")
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry.bind("<Return>", self.send_text)

        self.mic_btn = tk.Button(input_frame, text="🎤 Voice", bg="#1a1a2e", fg="#ffffff", font=("Segoe UI", 9, "bold"), command=self.toggle_mic)
        self.mic_btn.pack(side="right")

        # Check existing profile
        vp = load_voice_profile()
        if vp:
            self.auth_label.config(text=f"🔐 Voice Auth: ON ({len(vp.get('samples', []))} samples)", fg="#00ff88")

    def update_status(self, msg):
        self.root.after(0, lambda: self.status_label.config(text=msg))

    def update_auth_label(self, text, color):
        self.root.after(0, lambda: self.auth_label.config(text=text, fg=color))

    def update_wake_label(self, text, color):
        self.root.after(0, lambda: self.wake_label.config(text=text, fg=color))

    def update_mic_btn(self, text, color):
        self.root.after(0, lambda: self.mic_btn.config(text=text, bg=color))

    def add_message(self, sender, text):
        def _append():
            self.chat_log.insert(tk.END, f"{sender}: {text}\n\n")
            self.chat_log.see(tk.END)
        self.root.after(0, _append)

    def speak_cb(self, text):
        state = {
            "voice_mode": sr_module.voice_mode,
            "awake": sr_module.awake,
            "auto_listen_func": lambda: sr_module.auto_listen(
                self.update_status, self.update_wake_label, self.add_message, self.route_input, self.speak_cb
            )
        }
        speak(text, add_msg_callback=self.add_message, status_callback=self.update_status, process_input_callback=self.route_input, voice_state=state)

    def route_input(self, text):
        process_input(text, self.update_status, self.add_message, self.speak_cb)

    def send_text(self, event=None):
        txt = self.entry.get().strip()
        if not txt: return
        self.entry.delete(0, tk.END)
        self.add_message("You", txt)
        threading.Thread(target=self.route_input, args=(txt,), daemon=True).start()

    def toggle_mic(self):
        sr_module.on_mic_click(
            self.update_mic_btn, self.update_status, self.update_wake_label,
            self.add_message, self.route_input, self.speak_cb
        )