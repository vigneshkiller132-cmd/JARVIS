import threading
import tkinter as tk
import config
from gui.interface import JARVISGUI
import voice.speech_recognition as sr_module
from services.reminders import _start_reminder_loop

def main():
    root = tk.Tk()
    app = JARVISGUI(root)

    # Start Wake Word Listening Thread
    threading.Thread(
        target=sr_module.wake_word_listener,
        args=(app.update_status, app.update_wake_label, app.speak_cb),
        daemon=True
    ).start()

    # Start Reminder Loop
    _start_reminder_loop(app.speak_cb)

    # Launch GUI Event Loop
    root.mainloop()

if __name__ == "__main__":
    main()