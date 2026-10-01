MODIFIERS = ('ctrl', 'alt', 'win')
CHORD = frozenset(MODIFIERS)


class HotkeyChord:
    def __init__(self, on_start, on_stop):
        self.on_start = on_start
        self.on_stop = on_stop
        self.pressed = set()
        self.recording = False

    @staticmethod
    def normalize(name):
        n = (name or '').lower()
        if 'ctrl' in n or 'control' in n:
            return 'ctrl'
        if 'alt' in n or 'option' in n:
            return 'alt'
        if 'win' in n or 'cmd' in n or 'super' in n or 'meta' in n or 'dash' in n:
            return 'win'
        return None

    def handle(self, name, is_down):
        key = self.normalize(name)
        if key is None:
            return False
        if is_down:
            if self.recording:
                return True
            if key in self.pressed:
                return True
            self.pressed.add(key)
            if self.pressed.issuperset(CHORD):
                self.recording = True
                self.pressed = set()
                self.on_start()
                return True
            return len(self.pressed) >= 2
        self.pressed.discard(key)
        if self.recording and key in MODIFIERS:
            self.recording = False
            self.pressed.clear()
            self.on_stop()
        return False
