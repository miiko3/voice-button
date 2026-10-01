import math
from array import array

RATES = (16000, 48000, 44100, 22050, 8000)
SOUNDDEVICE = None


def backend():
    global SOUNDDEVICE
    if SOUNDDEVICE is None:
        import sounddevice

        SOUNDDEVICE = sounddevice
    return SOUNDDEVICE
FLOOR_DB = -60.0
CEIL_DB = -12.0
SPAN = CEIL_DB - FLOOR_DB
BLOCK_FRAMES = 1024


def level_from_pcm(data):
    samples = array('h')
    samples.frombytes(data)
    count = len(samples)
    if not count:
        return 0.0
    total = 0
    for value in samples:
        total += value * value
    rms = math.sqrt(total / count) / 32768.0
    if rms <= 1e-7:
        return 0.0
    value = (20.0 * math.log10(rms) - FLOOR_DB) / SPAN
    if value <= 0.0:
        return 0.0
    return 1.0 if value >= 1.0 else value


class Recorder:
    def __init__(self, rate=16000):
        self.rate = rate
        self.level = 0.0
        self.running = False
        self._stream = None
        self._audio_cb = None
        self._level_cb = None

    def bind(self, audio_cb=None, level_cb=None):
        self._audio_cb = audio_cb
        self._level_cb = level_cb

    def start(self):
        if self.running:
            return
        self.level = 0.0
        self._open()
        self.running = True

    def stop(self):
        stream = self._stream
        self._stream = None
        self.running = False
        if stream is not None:
            try:
                stream.stop()
            finally:
                stream.close()
        self.level = 0.0

    def close(self):
        self.stop()

    def _open(self):
        sd = backend()
        error = None
        for rate in RATES:
            stream = None
            try:
                stream = sd.RawInputStream(
                    samplerate=rate,
                    channels=1,
                    dtype='int16',
                    blocksize=BLOCK_FRAMES,
                    callback=self._callback,
                )
                stream.start()
            except Exception as exc:
                error = error or exc
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
                continue
            self._stream = stream
            self.rate = rate
            return
        raise error or RuntimeError('microphone unavailable')

    def _callback(self, indata, frames, time_info, status):
        if not self.running:
            return
        data = bytes(indata)
        if not data:
            return
        audio_cb = self._audio_cb
        level_cb = self._level_cb
        if audio_cb is not None:
            try:
                audio_cb(data)
            except Exception:
                pass
        if level_cb is not None:
            try:
                level_cb(level_from_pcm(data))
            except Exception:
                pass
