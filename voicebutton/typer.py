import ctypes
import time
from ctypes import wintypes

user32 = ctypes.WinDLL('user32')
kernel32 = ctypes.WinDLL('kernel32')

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
INPUT_KEYBOARD = 1
VK_RETURN = 0x0D
VK_TAB = 0x09
BATCH_CHARS = 24
BATCH_PAUSE = 0.008


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ('wVk', wintypes.WORD),
        ('wScan', wintypes.WORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.POINTER(ctypes.c_ulong)),
    ]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ('dx', wintypes.LONG),
        ('dy', wintypes.LONG),
        ('mouseData', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.POINTER(ctypes.c_ulong)),
    ]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ('uMsg', wintypes.DWORD),
        ('wParamL', wintypes.WORD),
        ('wParamH', wintypes.WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [('mi', _MOUSEINPUT), ('ki', _KEYBDINPUT), ('hi', _HARDWAREINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [('type', wintypes.DWORD), ('u', _INPUTUNION)]


user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(_INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT


def _code(char):
    value = ord(char)
    if value > 0xFFFF:
        value -= 0x10000
        return [0xD800 + (value >> 10), 0xDC00 + (value & 0x3FF)]
    return [value]


def _plan(text):
    events = []
    for char in text:
        if char == '\n':
            events.append((VK_RETURN, 0))
            events.append((VK_RETURN, KEYEVENTF_KEYUP))
            continue
        if char == '\t':
            events.append((VK_TAB, 0))
            events.append((VK_TAB, KEYEVENTF_KEYUP))
            continue
        for unit in _code(char):
            events.append((unit, KEYEVENTF_UNICODE))
            events.append((unit, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
    return events


def _flush(batch):
    if not batch:
        return
    items = (_INPUT * len(batch))()
    for index, (unit, flags) in enumerate(batch):
        items[index].type = INPUT_KEYBOARD
        items[index].u.ki = _KEYBDINPUT(wVk=0, wScan=unit, dwFlags=flags, time=0, dwExtraInfo=None)
    user32.SendInput(len(batch), items, ctypes.sizeof(_INPUT))


def type_text(text, batch_chars=BATCH_CHARS):
    if not text:
        return
    events = _plan(text)
    limit = max(2, batch_chars * 2)
    for start in range(0, len(events), limit):
        _flush(events[start:start + limit])
        time.sleep(BATCH_PAUSE)


def foreground_handle():
    return user32.GetForegroundWindow()


def focus_window(hwnd):
    if not hwnd:
        return
    try:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)
        target_tid = user32.GetWindowThreadProcessId(hwnd, None)
        cur_tid = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
        cur_thread = kernel32.GetCurrentThreadId()
        attached = False
        if cur_tid != cur_thread:
            attached = user32.AttachThreadInput(cur_tid, cur_thread, True) != 0
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        if attached:
            user32.AttachThreadInput(cur_tid, cur_thread, False)
    except Exception:
        pass
    time.sleep(0.1)
