import ctypes
import os
import re
import time
import wave

import numpy as np
import pytest

from voicebutton.transcriber import Transcriber, resolve_model_path
from voicebutton.typer import focus_window, type_text

PHRASE = 'привет как дела сегодня хорошая погода за окном светит солнце'
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'phrase_ru.wav')


def normalize(text):
    text = text or ''
    text = re.sub(r'[^\w\s]', '', text.lower(), flags=re.UNICODE)
    return re.sub(r'\s+', ' ', text).strip()


def overlap(text, phrase=PHRASE):
    result = normalize(text)
    words = normalize(phrase).split()
    return sum(w in result for w in words) / len(words)


def load_wav(path):
    with wave.open(path, 'rb') as handle:
        frames = handle.readframes(handle.getnframes())
    return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0


def test_transcription_pipeline():
    if not os.path.isdir(resolve_model_path()):
        pytest.skip('vosk model not found')
    audio = load_wav(DATA)
    assert audio.size > 0
    result = Transcriber().transcribe(audio)
    assert result, 'transcription returned empty text'
    assert overlap(result) >= 0.6, f'{result!r}'


def test_type_text_into_focused_widget():
    import tkinter as tk

    root = tk.Tk()
    root.title('voice-button-test')
    root.geometry('300x120')
    root.attributes('-topmost', True)
    widget = tk.Text(root)
    widget.pack(fill='both', expand=True)
    root.update()
    hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
    focus_window(hwnd)
    widget.focus_set()
    root.update()
    target = 'Привет мир'
    type_text(target)
    time.sleep(0.3)
    root.update()
    content = widget.get('1.0', 'end')
    root.destroy()
    assert target in content, f'expected {target!r} in {content!r}'


class FakeCapsule:
    def __init__(self):
        self.messages = []
        self.level_source = None

    def set_level_source(self, fn):
        self.level_source = fn

    def post(self, message):
        self.messages.append(message)


class FakeRecorder:
    def __init__(self, audio):
        self.audio = audio
        self.level = 0.0
        self.started = False

    def start(self):
        self.started = True

    def stop(self):
        self.started = False
        return self.audio

    def close(self):
        self.started = False


def test_app_dictation_end_to_end():
    import tkinter as tk

    from voicebutton.app import VoiceButtonApp

    if not os.path.isdir(resolve_model_path()):
        pytest.skip('vosk model not found')
    audio = load_wav(DATA)

    root = tk.Tk()
    root.geometry('400x160')
    root.attributes('-topmost', True)
    widget = tk.Text(root)
    widget.pack(fill='both', expand=True)
    root.update()
    hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
    focus_window(hwnd)
    widget.focus_set()
    root.update()

    capsule = FakeCapsule()
    recorder = FakeRecorder(audio)
    app = VoiceButtonApp(capsule=capsule, recorder=recorder, transcriber=Transcriber())
    try:
        app.start()
        assert app.recording is True
        assert recorder.started is True
        app.stop()
        deadline = time.time() + 30
        content = ''
        while time.time() < deadline:
            root.update()
            time.sleep(0.1)
            content = widget.get('1.0', 'end')
            if not app.busy and content.strip():
                break
    finally:
        app.close()
        root.destroy()

    assert overlap(content) >= 0.6, f'{normalize(content)!r}'