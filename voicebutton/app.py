import os
import threading

import keyboard

from .capsule import Capsule
from .hotkeys import HotkeyChord
from .recorder import Recorder
from .transcriber import Transcriber
from .typer import focus_window, foreground_handle, type_text

IDLE_RELEASE = 60.0
READY = 'Готов к диктовке'


class VoiceButtonApp:
    def __init__(self, capsule=None, recorder=None, transcriber=None):
        self.capsule = capsule or Capsule()
        self.recorder = recorder or Recorder()
        self.transcriber = transcriber or Transcriber()
        self.recording = False
        self.busy = False
        self.target = None
        self.session = None
        self._timer = None
        self.capsule.set_level_source(lambda: self.recorder.level)
        self.chord = HotkeyChord(self.start, self.stop)
        keyboard.hook(self._on_event)
        self.notify_ready()

    def notify_ready(self):
        if not os.path.isdir(self.transcriber.model_path):
            self.capsule.post(('error', 'Модель не найдена'))
            return
        self.capsule.post(('show', 'startup', READY))

    def _on_event(self, event):
        suppress = self.chord.handle(event.name, event.event_type == 'down')
        if suppress:
            event.suppress = True

    def start(self):
        if self.recording or self.busy:
            return
        self._cancel_release()
        self.recording = True
        self.target = foreground_handle()
        try:
            self.recorder.start()
        except Exception:
            self.recording = False
            self.capsule.post(('error', 'Нет микрофона'))
            return
        self.session = self.transcriber.begin(self.recorder.rate)
        self.recorder.bind(audio_cb=self.session.push)
        self.capsule.post(('show', 'recording'))

    def stop(self):
        if not self.recording:
            return
        self.recording = False
        self.busy = True
        session = self.session
        self.session = None
        try:
            self.recorder.stop()
        except Exception:
            pass
        self.recorder.bind(audio_cb=None, level_cb=None)
        self.capsule.post(('show', 'processing'))
        threading.Thread(target=self._finish, args=(session,), name='vb-type', daemon=True).start()

    def _finish(self, session):
        try:
            text = session.finish() if session is not None else ''
            if text:
                focus_window(self.target)
                type_text(text)
        except Exception:
            self.capsule.post(('error', 'Ошибка распознавания'))
        finally:
            self.busy = False
            self.capsule.post(('hide',))
            self._schedule_release()

    def _schedule_release(self):
        self._cancel_release()
        timer = threading.Timer(IDLE_RELEASE, self._release)
        timer.daemon = True
        self._timer = timer
        timer.start()

    def _cancel_release(self):
        timer = self._timer
        self._timer = None
        if timer is not None:
            timer.cancel()

    def _release(self):
        self._timer = None
        try:
            self.transcriber.unload()
        except Exception:
            pass

    def close(self):
        self._cancel_release()
        if self.session is not None:
            self.session.cancel()
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self.recorder.close()
        self.transcriber.unload()
        self.capsule.post(('quit',))
