import ctypes

def minimize_all():
    ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x44, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x44, 0, 2, 0)
    ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)

def restore_all():
    ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x4D, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x4D, 0, 2, 0)
    ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)
    ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)