import ctypes
import time
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004


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


def _send_unicode(code, keyup):
    flags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if keyup else 0)
    item = _INPUT()
    item.type = 1
    item.u.ki = _KEYBDINPUT(wVk=0, wScan=code, dwFlags=flags, time=0, dwExtraInfo=None)
    user32.SendInput(1, ctypes.byref(item), ctypes.sizeof(_INPUT))


def _type_char(char):
    code = ord(char)
    if code > 0xFFFF:
        code -= 0x10000
        units = [0xD800 + (code >> 10), 0xDC00 + (code & 0x3FF)]
    else:
        units = [code]
    for unit in units:
        _send_unicode(unit, False)
        _send_unicode(unit, True)
    time.sleep(0.004)


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


def type_text(text):
    if not text:
        return
    for char in text:
        _type_char(char)
    time.sleep(0.05)