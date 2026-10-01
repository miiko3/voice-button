import time

import pytest

WS_EX_LAYERED = 0x00080000

from voicebutton.capsule import (    BARS,
    GWL_EXSTYLE,
    HEIGHT,
    WS_EX_NOACTIVATE,
    WS_EX_TOOLWINDOW,
    WS_EX_TRANSPARENT,
    WIDTH,
    Capsule,
    user32,
)


@pytest.fixture
def capsule():
    return Capsule()


def pump(capsule, seconds=0.35):
    capsule.root.after(int(seconds * 1000), capsule.quit)
    capsule.run()


def settle(capsule, rounds=6):
    for _ in range(rounds):
        pump(capsule, 0.12)


def close(capsule):
    capsule.post(('quit',))
    pump(capsule, 0.1)
    try:
        capsule.root.destroy()
    except Exception:
        pass


def bar_heights(capsule):
    return [capsule.canvas.coords(bar)[3] - capsule.canvas.coords(bar)[1] for bar in capsule._bars]


def test_startup_notice_appears_and_hides(capsule):
    capsule.post(('show', 'startup', 'Готов к диктовке'))
    pump(capsule, 0.4)
    assert capsule._state == 'startup'
    assert capsule.root.state() == 'normal'
    assert capsule.canvas.itemcget(capsule._label, 'text') == 'Готов к диктовке'
    assert capsule.canvas.itemcget(capsule._bars[0], 'fill') == '#66c2ff'
    capsule.post(('hide',))
    settle(capsule)
    assert capsule._state == 'idle'
    assert capsule.root.state() == 'withdrawn'
    close(capsule)


def test_capsule_shape_is_max_rounded(capsule):
    c = capsule.canvas
    shapes = [c.type(item) for item in c.find_all()]
    assert shapes.count('oval') >= 2
    caps = [c.coords(item) for item in c.find_all() if c.type(item) == 'oval']
    assert all(abs(coords[3] - coords[1] - HEIGHT) < 1.5 for coords in caps)
    assert caps[0][:2] == [0.0, 0.0]
    assert caps[1][2] == float(WIDTH)
    close(capsule)


def test_recording_reacts_to_voice(capsule):
    capsule.set_level_source(lambda: 0.95)
    capsule.post(('show', 'recording'))
    pump(capsule, 0.6)
    assert capsule.canvas.itemcget(capsule._label, 'text') == 'Диктовка…'
    assert capsule._level > 0.5
    assert max(bar_heights(capsule)) > 16
    assert len(capsule._bars) == BARS
    close(capsule)


def test_quiet_input_shrinks_bars(capsule):
    capsule.set_level_source(lambda: 0.9)
    capsule.post(('show', 'recording'))
    pump(capsule, 0.5)
    loud = max(bar_heights(capsule))
    capsule.set_level_source(lambda: 0.0)
    pump(capsule, 1.5)
    quiet = max(bar_heights(capsule))
    assert quiet < loud
    assert quiet < 14
    close(capsule)


def test_processing_state(capsule):
    capsule.post(('show', 'processing'))
    pump(capsule, 0.3)
    assert capsule.canvas.itemcget(capsule._label, 'text') == 'Обработка…'
    first = [round(v, 1) for v in capsule.canvas.coords(capsule._bars[2])]
    pump(capsule, 0.3)
    second = [round(v, 1) for v in capsule.canvas.coords(capsule._bars[2])]
    assert first != second
    assert capsule.canvas.itemcget(capsule._bars[2], 'fill') == '#ffb454'
    close(capsule)


def test_error_shows_and_expires(capsule):
    capsule.post(('error', 'Нет микрофона'))
    pump(capsule, 0.3)
    assert capsule.canvas.itemcget(capsule._label, 'text') == 'Нет микрофона'
    assert capsule.canvas.itemcget(capsule._bars[0], 'fill') == '#ff5f56'
    capsule._err_until = time.monotonic() + 0.05
    settle(capsule)
    assert capsule._state == 'idle'
    close(capsule)


def test_long_message_is_trimmed(capsule):
    long_text = 'Ошибка распознавания очень длинного сообщения'
    capsule.post(('error', long_text))
    pump(capsule, 0.3)
    text = capsule.canvas.itemcget(capsule._label, 'text')
    assert text.endswith('…')
    assert len(text) <= 31
    close(capsule)


def test_state_switch_clears_level(capsule):
    capsule.set_level_source(lambda: 0.9)
    capsule.post(('show', 'recording'))
    pump(capsule, 0.4)
    capsule.post(('show', 'processing'))
    pump(capsule, 0.3)
    capsule.post(('error', 'Нет микрофона'))
    pump(capsule, 0.3)
    assert capsule.canvas.itemcget(capsule._bars[0], 'fill') == '#ff5f56'
    close(capsule)


def test_idle_state_skips_animation(capsule):
    capsule.post(('show', 'recording'))
    pump(capsule, 0.3)
    capsule.post(('hide',))
    settle(capsule)
    first = capsule._phase
    pump(capsule, 0.4)
    assert capsule._phase == first
    close(capsule)


def test_click_through_style(capsule):
    hwnd = capsule._hwnd()
    assert hwnd
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    assert style & WS_EX_TRANSPARENT
    assert style & WS_EX_NOACTIVATE
    assert style & WS_EX_TOOLWINDOW
    close(capsule)


def test_transparency_is_tk_owned(capsule):
    assert str(capsule.root.attributes('-transparentcolor')) == '#ff00ff'
    assert float(capsule.root.attributes('-alpha')) == 0.88
    close(capsule)
