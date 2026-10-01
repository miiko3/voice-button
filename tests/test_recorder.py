import os
import wave

import pytest

from voicebutton.recorder import Recorder, level_from_pcm
from voicebutton.transcriber import pcm_from_samples

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'phrase_ru.wav')


def read_pcm(path=DATA):
    with wave.open(path, 'rb') as handle:
        return handle.readframes(handle.getnframes()), handle.getframerate()


def frame(samples):
    return b''.join(int(v).to_bytes(2, 'little', signed=True) for v in samples)


def test_speech_level_is_high():
    pcm, _ = read_pcm()
    level = level_from_pcm(pcm)
    assert 0.5 < level <= 1.0, level


def test_quiet_room_stays_flat():
    assert level_from_pcm(frame([0, 0, 0, 0])) == 0.0
    assert level_from_pcm(frame([12, -12, 8, -8])) == 0.0


def test_level_grows_with_volume():
    soft = level_from_pcm(frame([int(300 * (1 if i % 2 else -1)) for i in range(512)]))
    loud = level_from_pcm(frame([int(6000 * (1 if i % 2 else -1)) for i in range(512)]))
    full = level_from_pcm(frame([32000 if i % 2 else -32000 for i in range(512)]))
    assert 0.0 < soft < loud < 1.0
    assert full == 1.0


def test_empty_input():
    assert level_from_pcm(b'') == 0.0


def test_pcm_from_samples_accepts_bytes_and_floats():
    assert pcm_from_samples(b'\x01\x02') == b'\x01\x02'
    out = pcm_from_samples([0.0, 1.0, -1.0])
    assert out == frame([0, 32767, -32767])


def has_input_device():
    try:
        import sounddevice as sd

        return any(device['max_input_channels'] > 0 for device in sd.query_devices())
    except Exception:
        return False


def test_recorder_starts_and_stops():
    if not has_input_device():
        pytest.skip('no input device available')
    recorder = Recorder()
    chunks = []
    levels = []
    recorder.bind(audio_cb=chunks.append, level_cb=levels.append)
    try:
        recorder.start()
        assert recorder.rate in (16000, 48000, 44100, 22050, 8000)
        deadline = 4.0
        import time

        start = time.monotonic()
        while not chunks and time.monotonic() - start < deadline:
            time.sleep(0.05)
        assert chunks, 'microphone produced no audio'
        assert all(0.0 <= value <= 1.0 for value in levels)
    finally:
        recorder.close()
    assert recorder.level == 0.0


def test_recorder_bind_can_be_cleared():
    recorder = Recorder()
    recorder.bind(audio_cb=lambda data: None)
    recorder.bind(audio_cb=None, level_cb=None)
    assert recorder._audio_cb is None
    assert recorder._level_cb is None
