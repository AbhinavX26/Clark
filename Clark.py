import os
import re
import subprocess
import tempfile
import threading
import tkinter as tk
from tkinter import messagebox
from difflib import SequenceMatcher

import speech_recognition as sr
from faster_whisper import WhisperModel


APP_NAME = "Clark"
WAKE_PHRASE = "hey clark"
# Whisper uses "en" for English; it handles accents without a regional language code.
LANGUAGE = "en"
WHISPER_MODEL_SIZE = "small"  # Better recognition than tiny/base; slower on older CPUs.
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"  # Lower memory use on typical Windows CPUs.

COMMANDS = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "file explorer": ["explorer.exe"],
    "task manager": ["taskmgr.exe"],
    "command prompt": ["cmd.exe"],
    "powershell": ["powershell.exe"],
    "control panel": ["control.exe"],
}

WAKE_VARIANTS = [
    "hey clark", "hey clerk", "hey clarke",
    "hey carl", "hey dark", "a clark",
]

# Common alternatives and likely speech-recognition mishearings.
COMMAND_ALIASES = {
    "notepad": ["notepad", "note pad", "open notepad", "start notepad"],
    "calculator": [
        "calculator", "calculate", "calculater", "calculated", "calculator app",
        "open calculator", "start calculator", "calc", "open calc",
    ],
    "task manager": [
        "task manager", "taskmanager", "tasks manager", "task man", "task manager app",
        "open task manager", "start task manager", "open taskmanager", "open tasks",
    ],
    "paint": ["paint", "open paint", "start paint", "ms paint"],
    "file explorer": [
        "file explorer", "files explorer", "open file explorer",
        "open explorer", "explorer",
    ],
    "command prompt": [
        "command prompt", "open command prompt", "open cmd", "cmd",
    ],
    "powershell": ["powershell", "power shell", "open powershell"],
    "control panel": ["control panel", "open control panel"],
}

recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold = 0.65
recognizer.non_speaking_duration = 0.35

# Loaded lazily in a worker thread, so the window can open immediately.
whisper_model = None
model_lock = threading.Lock()
stop_event = threading.Event()
busy = False
wake_verified = False
closing = False


def ui_status(message):
    """Schedule a status update on Tkinter's main thread."""
    try:
        root.after(0, lambda: status_label.config(text=message))
    except (tk.TclError, RuntimeError):
        pass


def show_microphone_error(message):
    try:
        root.after(
            0,
            lambda: messagebox.showerror("Microphone problem", message)
            if not closing else None,
        )
    except (tk.TclError, RuntimeError):
        pass


def normalize(text):
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def phrase_similarity(first, second):
    return SequenceMatcher(None, first, second).ratio()


def find_wake_phrase(text):
    text = normalize(text)
    words = text.split()

    if not words:
        return False, ""

    for i in range(len(words) - 1):
        pair = " ".join(words[i:i + 2])
        for variant in WAKE_VARIANTS:
            if pair == variant or phrase_similarity(pair, variant) >= 0.80:
                return True, " ".join(words[i + 2:]).strip()

    first_words = " ".join(words[:2])
    if phrase_similarity(first_words, WAKE_PHRASE) >= 0.86:
        return True, " ".join(words[2:]).strip()

    return False, ""


def match_command(spoken_text):
    """Match a command even if speech recognition makes a small mistake."""
    text = normalize(spoken_text)
    if not text:
        return None

    # Exact match against known command names and aliases.
    for app, aliases in COMMAND_ALIASES.items():
        if text == app or text in aliases:
            return app

    # Handle phrases such as "please open the calculator".
    cleaned = text
    for filler in ("please", "can you", "could you", "will you", "the", "open", "start"):
        cleaned = re.sub(rf"\b{re.escape(filler)}\b", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    for app, aliases in COMMAND_ALIASES.items():
        candidates = [app] + aliases
        for candidate in candidates:
            if cleaned == candidate:
                return app
            # Similarity helps with small mishearings like "calculater".
            if len(cleaned) >= 4 and phrase_similarity(cleaned, candidate) >= 0.78:
                return app

    # Recognize a known command embedded in a longer transcript.
    for app, aliases in COMMAND_ALIASES.items():
        for candidate in [app] + aliases:
            if candidate in text:
                return app

    return None


def launch_application(command):
    app = match_command(command)

    if app is None:
        ui_status(f'I heard "{command}", but did not match a command. Try "open Calculator".')
        return

    try:
        subprocess.Popen(COMMANDS[app], shell=False)
        ui_status(f"Opened {app.title()}!")
    except OSError as error:
        ui_status(f"Could not open {app}: {error}")


def get_microphone():
    try:
        return sr.Microphone()
    except (OSError, AttributeError) as error:
        show_microphone_error(
            "Clark could not access a microphone.\n\n"
            "Check that a microphone is connected and enabled in "
            "Windows Settings > System > Sound.\n\n"
            f"Details: {error}"
        )
        return None


def get_whisper_model():
    """Load the local model once. The first run downloads model files."""
    global whisper_model
    if whisper_model is not None:
        return whisper_model

    with model_lock:
        if whisper_model is None:
            ui_status(
                f"Loading Whisper {WHISPER_MODEL_SIZE} model... "
                "First run downloads it; please wait."
            )
            whisper_model = WhisperModel(
                WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
            )
    return whisper_model


def transcribe_audio(audio):
    """Transcribe SpeechRecognition audio with local faster-whisper."""
    model = get_whisper_model()
    wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
            wav_file.write(wav_bytes)
            temp_path = wav_file.name

        segments, _info = model.transcribe(
            temp_path,
            language=LANGUAGE,
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        if not text:
            raise sr.UnknownValueError()
        return text
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def test_microphone():
    global busy
    if busy:
        return

    busy = True
    test_button.config(state="disabled")
    start_button.config(state="disabled")
    stop_button.config(state="disabled")
    ui_status("Checking microphone and background noise...")
    threading.Thread(target=run_microphone_test, daemon=True).start()


def run_microphone_test():
    global busy
    microphone = get_microphone()

    if microphone is None:
        root.after(0, finish_test, False)
        busy = False
        return

    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            ui_status('Say "Hey Clark" or another accepted wake phrase.')
            audio = recognizer.listen(source, timeout=12, phrase_time_limit=10)

        transcript = transcribe_audio(audio)
        detected, _ = find_wake_phrase(transcript)

        if detected:
            ui_status(f'Wake phrase verified! Heard: "{transcript}". You can now start Clark.')
            root.after(0, finish_test, True)
        else:
            ui_status(f'Heard "{transcript}", but no accepted wake phrase was detected. Try again.')
            root.after(0, finish_test, False)

    except sr.WaitTimeoutError:
        ui_status("No speech detected. Try again and speak clearly.")
        root.after(0, finish_test, False)
    except sr.UnknownValueError:
        ui_status("Could not understand the speech. Try saying 'Hey Clark' in a quieter room.")
        root.after(0, finish_test, False)
    except sr.RequestError:
        ui_status("Whisper could not load or transcribe. Check the setup and try again.")
        root.after(0, finish_test, False)
    except Exception as error:
        ui_status(f"Whisper/microphone error: {error}")
        root.after(0, finish_test, False)
    finally:
        busy = False


def finish_test(success):
    global wake_verified
    wake_verified = success
    test_button.config(state="normal")
    start_button.config(state="normal" if success else "disabled")
    stop_button.config(state="disabled")


def start_listening():
    global busy
    if busy or not wake_verified:
        return

    busy = True
    stop_event.clear()
    test_button.config(state="disabled")
    start_button.config(state="disabled")
    stop_button.config(state="normal")
    ui_status('Clark is listening for "Hey Clark"...')
    threading.Thread(target=listen_loop, daemon=True).start()


def stop_listening():
    if not busy:
        return
    stop_event.set()
    stop_button.config(state="disabled")
    ui_status("Stopping Clark's listener...")


def finish_listening():
    global busy
    busy = False
    test_button.config(state="normal")
    start_button.config(state="normal" if wake_verified else "disabled")
    stop_button.config(state="disabled")

    if stop_event.is_set():
        ui_status("Clark is stopped. Click Start Clark to resume.")
    else:
        ui_status("Clark's listener has ended. You can restart it.")


def listen_loop():
    microphone = get_microphone()
    if microphone is None:
        root.after(0, finish_listening)
        return

    try:
        with microphone as source:
            ui_status('Listening for "Hey Clark"...')

            while not stop_event.is_set():
                try:
                    audio = recognizer.listen(source, timeout=3, phrase_time_limit=8)
                except sr.WaitTimeoutError:
                    continue

                if stop_event.is_set():
                    break

                try:
                    spoken = transcribe_audio(audio)
                except sr.UnknownValueError:
                    continue
                except sr.RequestError:
                    ui_status("Whisper could not transcribe that audio. Try speaking clearly.")
                    continue
                except Exception as error:
                    ui_status(f"Whisper error: {error}")
                    continue

                detected, command = find_wake_phrase(spoken)
                if not detected:
                    continue

                # If the wake phrase and command were said in one sentence.
                if command:
                    ui_status(f'Heard after wake phrase: "{command}"')
                    launch_application(command)
                    if not stop_event.is_set():
                        root.after(
                            1800,
                            lambda: ui_status('Listening for "Hey Clark"...')
                            if not stop_event.is_set() else None,
                        )
                    continue

                ui_status("Wake phrase detected! Now say your command.")

                try:
                    command_audio = recognizer.listen(
                        source, timeout=10, phrase_time_limit=8
                    )
                    if stop_event.is_set():
                        break

                    command_text = transcribe_audio(command_audio)
                    ui_status(f'Heard command: "{command_text}"')
                    launch_application(command_text)

                except sr.WaitTimeoutError:
                    ui_status("No command heard. Listening again...")
                except sr.UnknownValueError:
                    ui_status("I heard speech but couldn't understand it. Try saying 'open Calculator'.")
                except sr.RequestError:
                    ui_status("Whisper could not transcribe that audio. Try again.")
                except Exception as error:
                    ui_status(f"Whisper error: {error}")

                if not stop_event.is_set():
                    # Keep the command result visible briefly, then resume wake-word listening.
                    root.after(
                        1800,
                        lambda: ui_status('Listening for "Hey Clark"...')
                        if not stop_event.is_set() else None,
                    )

    except (OSError, AttributeError) as error:
        ui_status(f"Microphone error: {error}")
    finally:
        try:
            root.after(0, finish_listening)
        except (tk.TclError, RuntimeError):
            pass


def close_app():
    global closing
    closing = True
    stop_event.set()
    try:
        root.destroy()
    except tk.TclError:
        pass


# ----------------- User interface -----------------

root = tk.Tk()
root.title(APP_NAME)
root.geometry("390x330")
root.resizable(False, False)
root.attributes("-topmost", True)
root.configure(bg="#171923")
root.protocol("WM_DELETE_WINDOW", close_app)

title_label = tk.Label(
    root, text="Clark", font=("Segoe UI", 19, "bold"),
    fg="white", bg="#171923",
)
title_label.pack(pady=(12, 3))

status_label = tk.Label(
    root, text="Local Whisper recognition. First, test your microphone.", font=("Segoe UI", 9),
    fg="#c3cbe0", bg="#171923", wraplength=350, justify="center",
)
status_label.pack(pady=8)

test_button = tk.Button(
    root, text="1. Test Microphone", command=test_microphone,
    bg="#303548", fg="white", activebackground="#454d66",
    activeforeground="white", relief="flat", padx=12, pady=5,
)
test_button.pack(pady=4)

start_button = tk.Button(
    root, text="2. Start Clark", command=start_listening,
    state="disabled", bg="#3b6b54", fg="white",
    activebackground="#4d8568", activeforeground="white",
    relief="flat", padx=12, pady=5,
)
start_button.pack(pady=4)

stop_button = tk.Button(
    root, text="3. Stop Listening", command=stop_listening,
    state="disabled", bg="#754747", fg="white",
    activebackground="#925858", activeforeground="white",
    relief="flat", padx=12, pady=5,
)
stop_button.pack(pady=4)

exit_button = tk.Button(
    root, text="Exit", command=close_app, bg="#303548", fg="white",
    activebackground="#454d66", activeforeground="white",
    relief="flat", padx=16, pady=3,
)
exit_button.pack(pady=(4, 10))

root.mainloop()
