import threading

import keyboard

from .capsule import Capsule
from .hotkeys import HotkeyChord
from .recorder import Recorder
from .transcriber import Transcriber
from .typer import focus_window, foreground_handle, type_text


class VoiceButtonApp:
    def __init__(self, capsule=None, recorder=None, transcriber=None):
        self.capsule = capsule or Capsule()
        self.recorder = recorder or Recorder()
        self.transcriber = transcriber or Transcriber()
        self.recording = False
        self.busy = False
        self.target = None
        self.capsule.set_level_source(lambda: self.recorder.level)
        self.chord = HotkeyChord(self.start, self.stop)
        keyboard.hook(self._on_event)

    def _on_event(self, event):
        suppress = self.chord.handle(event.name, event.event_type == 'down')
        if suppress:
            event.suppress = True

    def start(self):
        if self.recording or self.busy:
            return
        self.recording = True
        self.target = foreground_handle()
        try:
            self.recorder.start()
        except Exception:
            self.recording = False
            self.capsule.post(('error', 'Нет микрофона'))
            return
        self.capsule.post(('show', 'recording', 'Диктовка…'))

    def stop(self):
        if not self.recording:
            return
        self.recording = False
        audio = self.recorder.stop()
        self.busy = True
        self.capsule.post(('show', 'processing', 'Обработка…'))
        threading.Thread(target=self._finish, args=(audio,), daemon=True).start()

    def _finish(self, audio):
        try:
            text = self.transcriber.transcribe(audio)
            if text:
                focus_window(self.target)
                type_text(text)
        except Exception:
            self.capsule.post(('error', 'Ошибка распознавания'))
        finally:
            self.busy = False
            self.capsule.post(('hide',))

    def close(self):
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self.recorder.close()
        self.capsule.post(('quit',))