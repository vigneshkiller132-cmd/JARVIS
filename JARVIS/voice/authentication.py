import json
import math
import os
import struct
import time
import datetime
import speech_recognition as sr
import config

voice_profile = None
VOICE_THRESHOLD = 0.82

def compute_mfcc(audio_data, n_mfcc=13, n_fft=512, hop=160, sr_rate=16000):
    try:
        raw = audio_data.get_raw_data(convert_rate=sr_rate, convert_width=2)
        samples = struct.unpack(f"{len(raw)//2}h", raw)
        signal = [s/32768.0 for s in samples]
        if len(signal) < n_fft: return None
        emp = [signal[0]] + [signal[i]-0.97*signal[i-1] for i in range(1, len(signal))]
        frames, n_bands = [], n_mfcc*2
        band_size = max(1, n_fft//(2*n_bands))
        for st in range(0, len(emp)-n_fft, hop):
            f = [emp[st+i]*(0.54-0.46*math.cos(2*math.pi*i/(n_fft-1))) for i in range(n_fft)]
            be = [math.log(sum(x*x for x in f[b*band_size:(b+1)*band_size])+1e-10) for b in range(n_bands)]
            frames.append([sum(be[b]*math.cos(math.pi*i*(b+0.5)/n_bands) for b in range(n_bands)) for i in range(n_mfcc)])
            if len(frames) >= 100: break
        if not frames: return None
        avg = [sum(f[i] for f in frames)/len(frames) for i in range(n_mfcc)]
        mean = sum(avg)/len(avg)
        std = math.sqrt(sum((x-mean)**2 for x in avg)/len(avg))+1e-10
        return [(x-mean)/std for x in avg]
    except Exception:
        return None

def cosine_sim(a, b):
    try:
        d = sum(x*y for x, y in zip(a, b))
        na = math.sqrt(sum(x*x for x in a))
        nb = math.sqrt(sum(x*x for x in b))
        return d/(na*nb) if na and nb else 0.0
    except Exception:
        return 0.0

def load_voice_profile():
    global voice_profile
    try:
        if os.path.exists(config.VOICE_FILE):
            with open(config.VOICE_FILE, "r") as f:
                voice_profile = json.load(f)
                return voice_profile
    except Exception:
        pass
    return None

def save_voice_profile(p):
    try:
        with open(config.VOICE_FILE, "w") as f:
            json.dump(p, f)
    except Exception:
        pass

def verify_voice(audio_data):
    if not voice_profile: return True
    feat = compute_mfcc(audio_data)
    if feat is None: return False
    scores = [cosine_sim(feat, s) for s in voice_profile.get("samples", [])]
    if not scores: return True
    best = max(scores)
    avg = sum(scores)/len(scores)
    final = best*0.6 + avg*0.4
    print(f"  [auth] best={best:.3f} avg={avg:.3f} final={final:.3f}")
    return final >= VOICE_THRESHOLD

def enroll_voice(speak_func, status_callback, auth_callback):
    global voice_profile
    phrases = [
        "Hey Jarvis I am your owner",
        "Hello Jarvis open my computer",
        "Jarvis my voice is my password",
        "Hey Jarvis good morning",
        "Okay Jarvis what is the time",
    ]
    speak_func(f"Starting voice enrollment {config.YOUR_NAME}. I will record 5 samples.")
    samples = []
    r = sr.Recognizer()
    r.energy_threshold = 300
    for i, phrase in enumerate(phrases):
        speak_func(f"Sample {i+1}. Say: {phrase}")
        status_callback(f"Recording sample {i+1} of 5...")
        time.sleep(0.3)
        try:
            with sr.Microphone() as src:
                r.adjust_for_ambient_noise(src, duration=0.4)
                audio = r.listen(src, timeout=8, phrase_time_limit=5)
                feat = compute_mfcc(audio)
                if feat:
                    samples.append(feat)
                    speak_func(f"Sample {i+1} saved.")
                else:
                    speak_func(f"Sample {i+1} failed.")
        except Exception:
            speak_func(f"Error on sample {i+1}.")
        time.sleep(0.3)
    if len(samples) >= 3:
        profile = {
            "samples": samples,
            "enrolled_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "owner": config.YOUR_NAME,
            "sample_count": len(samples)
        }
        save_voice_profile(profile)
        voice_profile = profile
        speak_func(f"Voice profile created with {len(samples)} samples {config.YOUR_NAME}.")
        auth_callback(f"🔐 Voice Auth: ON ({len(samples)} samples)", "#00ff88")
        return profile
    speak_func(f"Enrollment failed. Only {len(samples)} samples. Need at least 3.")
    return None

def reset_voice_profile(speak_func, auth_callback):
    global voice_profile
    voice_profile = None
    if os.path.exists(config.VOICE_FILE):
        os.remove(config.VOICE_FILE)
    speak_func(f"Voice profile deleted {config.YOUR_NAME}.")
    auth_callback("🔓 Voice Auth: OFF", "#ff4444")