import json
import os
import queue
import sys
import threading
import types

DEFAULT_MODEL = 'vosk-model-small-ru-0.22'
DEFAULT_RATE = 16000
QUEUE_LIMIT = 400
COMMA_GAP = 0.30
DOT_GAP = 1.0
STUB_MODULES = ('requests', 'srt', 'tqdm')

_VOSK = None


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


def _stub(name):
    module = types.ModuleType(name)

    def __getattr__(attr):
        if attr.startswith('__'):
            raise AttributeError(attr)
        return lambda *args, **kwargs: None

    module.__getattr__ = __getattr__
    return module


def load_vosk():
    global _VOSK
    if _VOSK is not None:
        return _VOSK
    hidden = {name: sys.modules.get(name) for name in STUB_MODULES}
    for name, module in hidden.items():
        if module is None:
            sys.modules[name] = _stub(name)
    try:
        import vosk
    except Exception:
        for name, module in hidden.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
        import vosk
    else:
        for name, module in hidden.items():
            if module is None:
                sys.modules.pop(name, None)
    vosk.SetLogLevel(-1)
    _VOSK = vosk
    return vosk


def new_recognizer(model, rate):
    recognizer = load_vosk().KaldiRecognizer(model, rate)
    recognizer.SetWords(True)
    return recognizer


def pcm_from_samples(data):
    if isinstance(data, (bytes, bytearray, memoryview)):
        return bytes(data)
    out = bytearray()
    for value in data:
        scaled = int(value * 32767.0)
        if scaled > 32767:
            scaled = 32767
        elif scaled < -32768:
            scaled = -32768
        out += int(scaled).to_bytes(2, 'little', signed=True)
    return bytes(out)


def join_words(text, words, last_end=None):
    for item in words:
        word = str(item.get('word') or '').strip()
        if not word:
            continue
        gap = 0.0
        start = item.get('start')
        end = item.get('end')
        if last_end is not None and start is not None:
            try:
                gap = round(float(start) - float(last_end), 3)
            except (TypeError, ValueError):
                gap = 0.0
        if not text:
            text = word
        elif gap >= DOT_GAP:
            text = text + '. ' + word
        elif gap >= COMMA_GAP:
            text = text + ', ' + word
        else:
            text = text + ' ' + word
        if end is not None:
            try:
                last_end = float(end)
            except (TypeError, ValueError):
                last_end = None
    return text, last_end


def finalize(text):
    text = ' '.join((text or '').split())
    if not text:
        return ''
    out = []
    sentence = True
    for char in text:
        if sentence and char.isalpha():
            out.append(char.upper())
            sentence = False
        else:
            out.append(char)
        if char in '.!?':
            sentence = True
    text = ''.join(out)
    if text[-1] not in '.!?':
        text += ' '
    return text


class Session:
    def __init__(self, transcriber, sample_rate=DEFAULT_RATE):
        self.transcriber = transcriber
        self.sample_rate = sample_rate
        self.partial = ''
        self.done = False
        self.error = None
        self._queue = queue.Queue(maxsize=QUEUE_LIMIT)
        self._text = ''
        self._last_end = None
        self._thread = threading.Thread(target=self._run, name='vb-stt', daemon=True)
        self._thread.start()

    def push(self, data):
        if self.done or not data:
            return
        try:
            self._queue.put_nowait(data)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(data)
            except queue.Full:
                pass

    def finish(self, timeout=180.0):
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            self._queue.get_nowait()
            self._queue.put_nowait(None)
        self._thread.join(timeout)
        if self.error:
            raise self.error
        return finalize(self._text)

    def cancel(self):
        self.done = True
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass

    def _run(self):
        try:
            recognizer = self.transcriber.acquire(self.sample_rate)
        except Exception as exc:
            self.error = exc
            self.done = True
            return
        try:
            drained = False
            while True:
                chunk = self._queue.get()
                if chunk is None:
                    drained = True
                    break
                try:
                    if recognizer.AcceptWaveform(chunk):
                        self._merge(json.loads(recognizer.Result()))
                    else:
                        payload = json.loads(recognizer.PartialResult())
                        self.partial = str(payload.get('partial') or '')
                except Exception as exc:
                    self.error = exc
                    break
            if drained:
                self._merge(json.loads(recognizer.FinalResult()))
        except Exception as exc:
            self.error = exc
        finally:
            self.partial = ''
            self.done = True
            self.transcriber.release()

    def _merge(self, payload):
        words = payload.get('result') if isinstance(payload, dict) else None
        if not words:
            return
        self._text, self._last_end = join_words(self._text, words, self._last_end)
        self.partial = ''


class Transcriber:
    def __init__(self, model_name=None, sample_rate=DEFAULT_RATE):
        self.sample_rate = sample_rate
        self.model_path = resolve_model_path(model_name)
        self.loaded = False
        self._model = None
        self._recognizer = None
        self._rate = None
        self._busy = 0
        self._lock = threading.Lock()

    def acquire(self, sample_rate=None):
        rate = sample_rate or self.sample_rate
        with self._lock:
            self._busy += 1
            try:
                if self._recognizer is None:
                    if not os.path.isdir(self.model_path):
                        raise FileNotFoundError(self.model_path)
                    vosk = load_vosk()
                    if self._model is None:
                        self._model = vosk.Model(self.model_path)
                        self.loaded = True
                    self._rate = rate
                    self._recognizer = new_recognizer(self._model, rate)
                elif self._rate != rate:
                    self._rate = rate
                    self._recognizer = new_recognizer(self._model, rate)
                self._recognizer.Reset()
                return self._recognizer
            except Exception:
                self._busy -= 1
                raise

    def release(self):
        with self._lock:
            if self._busy > 0:
                self._busy -= 1

    def unload(self):
        with self._lock:
            if self._busy > 0:
                return
            self._recognizer = None
            self._model = None
            self._rate = None
            self.loaded = False

    def begin(self, sample_rate=None):
        return Session(self, sample_rate or self.sample_rate)

    def transcribe(self, audio, sample_rate=None):
        session = self.begin(sample_rate)
        session.push(pcm_from_samples(audio))
        return session.finish()
