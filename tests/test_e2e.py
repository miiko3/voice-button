import ctypes
import os
import re
import time
import wave
from ctypes import wintypes

import numpy as np
import pytest

from voicebutton.transcriber import Transcriber, finalize, join_words, resolve_model_path
from voicebutton.typer import focus_window, type_text

user32 = ctypes.WinDLL('user32')
user32.GetParent.argtypes = [wintypes.HWND]
user32.GetParent.restype = wintypes.HWND

PHRASE = 'привет как дела сегодня хорошая погода за окном светит солнце'
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'phrase_ru.wav')


def hwnd_of(widget):
    top = widget.winfo_toplevel()
    return user32.GetParent(top.winfo_id()) or top.winfo_id()


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


def pcm_of(path):
    with wave.open(path, 'rb') as handle:
        frames = handle.readframes(handle.getnframes())
        rate = handle.getframerate()
    return frames, rate


def test_transcription_pipeline():
    if not os.path.isdir(resolve_model_path()):
        pytest.skip('vosk model not found')
    audio = load_wav(DATA)
    assert audio.size > 0
    result = Transcriber().transcribe(audio)
    assert result, 'transcription returned empty text'
    assert overlap(result) >= 0.6, f'{result!r}'


def test_streaming_matches_batch():
    if not os.path.isdir(resolve_model_path()):
        pytest.skip('vosk model not found')
    pcm, rate = pcm_of(DATA)
    transcriber = Transcriber(sample_rate=rate)
    session = transcriber.begin(rate)
    step = 2048
    for offset in range(0, len(pcm), step):
        session.push(pcm[offset:offset + step])
    streamed = session.finish()
    assert overlap(streamed) >= 0.6, f'{streamed!r}'
    transcriber.unload()
    batch = Transcriber(sample_rate=rate).transcribe(pcm, rate)
    assert normalize(streamed) == normalize(batch), f'{streamed!r} != {batch!r}'


def test_type_text_into_focused_widget():
    import tkinter as tk

    root = tk.Tk()
    root.title('voice-button-test')
    root.geometry('300x120')
    root.attributes('-topmost', True)
    widget = tk.Text(root)
    widget.pack(fill='both', expand=True)
    root.update()
    focus_window(hwnd_of(root))
    widget.focus_set()
    root.update()
    target = 'Привет мир'
    type_text(target)
    time.sleep(0.3)
    root.update()
    content = widget.get('1.0', 'end')
    root.destroy()
    assert target in content, f'expected {target!r} in {content!r}'


def test_pause_punctuation():
    words = [
        {'word': 'привет', 'start': 0.0, 'end': 0.4},
        {'word': 'мир', 'start': 1.6, 'end': 1.9},
    ]
    text, end = join_words('', words)
    assert text == 'привет. мир'
    assert end == pytest.approx(1.9)

    words = [
        {'word': 'привет', 'start': 0.0, 'end': 0.4},
        {'word': 'далее', 'start': 0.7, 'end': 0.9},
    ]
    text, _ = join_words('', words)
    assert text == 'привет, далее'

    text, _ = join_words('привет. мир', [{'word': 'как', 'start': 2.0, 'end': 2.2}])
    assert text == 'привет. мир как'


def test_finalize_shapes_text():
    assert finalize('') == ''
    assert finalize('  привет   мир  ') == 'Привет мир '
    assert finalize('привет. как дела') == 'Привет. Как дела '
    assert finalize('готово!') == 'Готово!'


class FakeCapsule:
    def __init__(self):
        self.messages = []
        self.level_source = None

    def set_level_source(self, fn):
        self.level_source = fn

    def post(self, message):
        self.messages.append(message)


class FakeRecorder:
    def __init__(self, pcm, rate=16000):
        self.pcm = pcm
        self.rate = rate
        self.level = 0.0
        self.started = False
        self.sink = None

    def bind(self, audio_cb=None, level_cb=None):
        self.sink = audio_cb

    def start(self):
        self.started = True

    def stop(self):
        self.started = False
        step = 2048
        if self.sink:
            for offset in range(0, len(self.pcm), step):
                self.sink(self.pcm[offset:offset + step])
        return self.pcm

    def close(self):
        self.started = False


def test_app_dictation_end_to_end():
    import tkinter as tk

    from voicebutton.app import VoiceButtonApp

    if not os.path.isdir(resolve_model_path()):
        pytest.skip('vosk model not found')
    pcm, rate = pcm_of(DATA)

    root = tk.Tk()
    root.geometry('400x160')
    root.attributes('-topmost', True)
    widget = tk.Text(root)
    widget.pack(fill='both', expand=True)
    root.update()
    focus_window(hwnd_of(root))
    widget.focus_set()
    root.update()

    capsule = FakeCapsule()
    recorder = FakeRecorder(pcm, rate)
    app = VoiceButtonApp(
        capsule=capsule,
        recorder=recorder,
        transcriber=Transcriber(sample_rate=rate),
    )
    try:
        app.start()
        assert app.recording is True
        assert recorder.started is True
        assert capsule.messages[-1][0] == 'show'
        app.stop()
        deadline = time.time() + 60
        while time.time() < deadline:
            root.update()
            time.sleep(0.1)
            if not app.busy:
                break
        time.sleep(0.5)
        root.update()
        content = widget.get('1.0', 'end')
    finally:
        app.close()
        root.destroy()

    assert overlap(content) >= 0.6, f'{normalize(content)!r}'
    states = [m for m in capsule.messages if m[0] in ('show', 'error', 'notice')]
    assert states[0][1] == 'startup'
    assert 'recording' in [m[1] for m in states]
    assert 'processing' in [m[1] for m in states]


def test_app_reports_missing_model():
    from voicebutton.app import VoiceButtonApp

    class FakeTranscriber:
        model_path = '/definitely/missing/model'

        def __init__(self):
            self.released = False

        def unload(self):
            self.released = True

    capsule = FakeCapsule()
    app = VoiceButtonApp(capsule=capsule, recorder=FakeRecorder(b''), transcriber=FakeTranscriber())
    assert capsule.messages[-1][0] == 'error'
    app.close()
