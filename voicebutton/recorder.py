import numpy as np
import sounddevice as sd


class Recorder:
    def __init__(self, rate=16000):
        self.rate = rate
        self.stream = None
        self.chunks = []
        self.level = 0.0

    def start(self):
        self.chunks = []
        self.level = 0.0

        def callback(indata, frames, time_info, status):
            mono = indata.reshape(-1).copy()
            self.chunks.append(mono)
            rms = float(np.sqrt(np.mean(mono * mono))) if mono.size else 0.0
            self.level = min(1.0, rms * 4.0)

        self.stream = sd.InputStream(
            samplerate=self.rate,
            channels=1,
            dtype='float32',
            callback=callback,
        )
        self.stream.start()

    def stop(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if not self.chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(self.chunks).astype(np.float32)

    def close(self):
        self.stop()