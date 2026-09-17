import json
import os
import sys

import numpy as np
from vosk import KaldiRecognizer, Model, SetLogLevel

DEFAULT_MODEL = 'vosk-model-small-ru-0.22'


def base_dir():
    if getattr(sys, '_MEIPASS', None):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_model_path(model_name=None):
    candidate = model_name or os.environ.get('VOICE_BUTTON_MODEL') or DEFAULT_MODEL
    if os.path.isdir(candidate):
        return os.path.abspath(candidate)
    bundled = os.path.join(base_dir(), 'models', candidate)
    if os.path.isdir(bundled):
        return bundled
    fallback = os.path.join(base_dir(), 'models', DEFAULT_MODEL)
    if os.path.isdir(fallback):
        return fallback
    return os.path.abspath(candidate)


class Transcriber:
    def __init__(self, model_name=None, sample_rate=16000):
        self.sample_rate = sample_rate
        self.model_path = resolve_model_path(model_name)
        self.model = None

    def _load(self):
        if self.model is None:
            SetLogLevel(-1)
            self.model = Model(self.model_path)
        return self.model

    def transcribe(self, audio, sample_rate=None):
        rate = sample_rate or self.sample_rate
        data = np.asarray(audio, dtype=np.float32)
        if data.size == 0:
            return ''
        model = self._load()
        pcm = (np.clip(data, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
        recognizer = KaldiRecognizer(model, rate)
        recognizer.AcceptWaveform(pcm)
        recognizer.AcceptWaveform(b'')
        result = json.loads(recognizer.FinalResult())
        text = (result.get('text') or '').strip()
        if text:
            text = text[0].upper() + text[1:]
        return text