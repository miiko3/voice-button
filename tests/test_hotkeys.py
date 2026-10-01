from voicebutton.hotkeys import HotkeyChord


def build():
    events = []
    chord = HotkeyChord(on_start=lambda: events.append('start'), on_stop=lambda: events.append('stop'))
    return chord, events


def test_partial_combo_does_not_trigger():
    chord, events = build()
    chord.handle('ctrl', True)
    chord.handle('win', True)
    assert events == []
    assert chord.recording is False


def test_full_chord_starts_and_release_stops():
    chord, events = build()
    for name in ('ctrl', 'win', 'alt'):
        chord.handle(name, True)
    assert events == ['start']
    assert chord.recording is True
    chord.handle('alt', False)
    assert events == ['start', 'stop']
    assert chord.recording is False


def test_chord_can_restart():
    chord, events = build()
    for name in ('ctrl', 'win', 'alt'):
        chord.handle(name, True)
    for name in ('ctrl', 'win', 'alt'):
        chord.handle(name, False)
    for name in ('alt', 'ctrl', 'win'):
        chord.handle(name, True)
    assert events.count('start') == 2
    assert events.count('stop') == 1


def test_auto_repeat_is_suppressed():
    chord, events = build()
    for name in ('ctrl', 'win', 'alt'):
        chord.handle(name, True)
    for _ in range(5):
        assert chord.handle('ctrl', True) is True
        assert chord.handle('alt', True) is True
    assert events == ['start']


def test_release_any_modifier_stops():
    chord, events = build()
    for name in ('ctrl', 'win', 'alt'):
        chord.handle(name, True)
    chord.handle('ctrl', False)
    assert events == ['start', 'stop']
    chord.handle('win', False)
    chord.handle('alt', False)
    assert events == ['start', 'stop']


def test_normalize():
    assert HotkeyChord.normalize('left ctrl') == 'ctrl'
    assert HotkeyChord.normalize('control') == 'ctrl'
    assert HotkeyChord.normalize('alt') == 'alt'
    assert HotkeyChord.normalize('windows') == 'win'
    assert HotkeyChord.normalize('left windows') == 'win'
    assert HotkeyChord.normalize('a') is None
    assert HotkeyChord.normalize(None) is None
