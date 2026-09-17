from voicebutton.hotkeys import HotkeyChord


def test_partial_combo_does_not_trigger():
    events = []
    chord = HotkeyChord(on_start=lambda: events.append('start'), on_stop=lambda: events.append('stop'))
    chord.handle('ctrl', True)
    chord.handle('win', True)
    assert events == []
    assert chord.recording is False


def test_full_chord_starts_and_release_stops():
    events = []
    chord = HotkeyChord(on_start=lambda: events.append('start'), on_stop=lambda: events.append('stop'))
    for name in ('ctrl', 'win', 'alt'):
        chord.handle(name, True)
    assert events == ['start']
    assert chord.recording is True
    chord.handle('alt', False)
    assert events == ['start', 'stop']
    assert chord.recording is False


def test_chord_can_restart():
    events = []
    chord = HotkeyChord(on_start=lambda: events.append('start'), on_stop=lambda: events.append('stop'))
    for name in ('ctrl', 'win', 'alt'):
        chord.handle(name, True)
    for name in ('ctrl', 'win', 'alt'):
        chord.handle(name, False)
    for name in ('alt', 'ctrl', 'win'):
        chord.handle(name, True)
    assert events.count('start') == 2
    assert events.count('stop') == 1


def test_normalize():
    assert HotkeyChord.normalize('left ctrl') == 'ctrl'
    assert HotkeyChord.normalize('control') == 'ctrl'
    assert HotkeyChord.normalize('alt') == 'alt'
    assert HotkeyChord.normalize('windows') == 'win'
    assert HotkeyChord.normalize('left windows') == 'win'
    assert HotkeyChord.normalize('a') is None
    assert HotkeyChord.normalize(None) is None