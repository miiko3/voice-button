import ctypes
import math
import os
import queue
import sys
import time
import tkinter as tk

BG = '#171a21'
ACCENT = '#66c2ff'
PROCESS = '#ffb454'
ERROR = '#ff5f56'
TEXT = '#e6edf3'
KEY = '#ff00ff'

WIDTH = 280
HEIGHT = 64


def asset_path(name):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, 'assets', name)


class Capsule:
    def __init__(self, width=WIDTH, height=HEIGHT):
        self.width = width
        self.height = height
        self._queue = queue.Queue()
        self._state = 'idle'
        self._message = ''
        self._level = 0.0
        self._phase = 0
        self._err_until = 0.0
        self._level_source = None
        self._bars = []
        self._label = None
        self._logo_source = None
        self._logo_image = None

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg=KEY)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.88)
        self.root.attributes('-transparentcolor', KEY)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - width) // 2
        y = sh - height - 96
        self.root.geometry(f'{width}x{height}+{x}+{y}')

        self.canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            bg=KEY,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill='both', expand=True)
        self._paint()
        self._load_logo()
        self.root.withdraw()
        self._make_click_through()
        self.root.after(25, self._tick)

    def set_level_source(self, fn):
        self._level_source = fn

    def post(self, message):
        self._queue.put(message)

    def run(self):
        self.root.mainloop()

    def quit(self):
        self.root.quit()

    def _paint(self):
        c = self.canvas
        w, h = self.width, self.height
        c.create_rectangle(0, 0, w, h, fill=BG, outline='')
        c.create_oval(0, 0, h, h, fill=BG, outline='')
        c.create_oval(w - h, 0, w, h, fill=BG, outline='')

        bx = 24
        bar_w = 7
        gap = 4
        for i in range(5):
            bar = c.create_rectangle(bx, h // 2 - 6, bx + bar_w, h // 2 + 6, fill=ACCENT, outline='')
            self._bars.append(bar)
            bx += bar_w + gap
        self._label = c.create_text(84, h // 2, text='', fill=TEXT, font=('Segoe UI', 13), anchor='w')

    def _load_logo(self):
        try:
            self._logo_source = tk.PhotoImage(file=asset_path('logo.png'))
        except Exception:
            self._logo_source = None
            return
        self._logo_image = self._logo_source.subsample(20, 20)
        self.canvas.create_image(self.width - 24, self.height // 2, image=self._logo_image, anchor='center')

    def _make_click_through(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            ex_style = ex_style | 0x20 | 0x08000000 | 0x00080000
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, ex_style)
        except Exception:
            pass

    def _tick(self):
        while True:
            try:
                message = self._queue.get_nowait()
            except queue.Empty:
                break
            kind = message[0]
            if kind == 'show':
                self._state = message[1]
                self._message = message[2] if len(message) > 2 else ''
                self._err_until = 0.0
                self.root.deiconify()
            elif kind == 'hide':
                self._state = 'idle'
                self.root.withdraw()
            elif kind == 'error':
                self._state = 'error'
                self._message = message[1]
                self._err_until = time.monotonic() + 3.0
                self.root.deiconify()
            elif kind == 'quit':
                self.root.quit()
                return
        self._animate()
        self.root.after(25, self._tick)

    def _animate(self):
        if self._state == 'idle':
            return
        now = time.monotonic()
        if self._state == 'error':
            if now >= self._err_until:
                self._state = 'idle'
                self.root.withdraw()
                return
        if self._state == 'recording' and self._level_source:
            raw = self._level_source()
            self._level = self._level * 0.7 + max(0.0, min(raw, 1.0)) * 0.3
        self._phase += 1
        self._update_bars()
        self._update_text()

    def _update_bars(self):
        c = self.canvas
        h = self.height
        max_dy = h // 2 - 10
        for i, bar in enumerate(self._bars):
            if self._state == 'processing':
                wave = 0.5 + 0.5 * math.sin(self._phase * 0.3 + i * 1.7)
                dy = 4 + wave * (max_dy - 4)
                fill = PROCESS
            else:
                wobble = 0.6 + 0.4 * math.sin(self._phase * 0.35 + i * 1.3)
                dy = 4 + self._level * wobble * (max_dy - 4)
                fill = ACCENT if self._state == 'recording' else ERROR
            c.coords(bar, 24 + i * 11, h // 2 - dy, 24 + i * 11 + 7, h // 2 + dy)
            c.itemconfigure(bar, fill=fill)

    def _update_text(self):
        if self._state == 'recording':
            text = 'Диктовка…'
        elif self._state == 'processing':
            text = 'Обработка…'
        else:
            text = self._message
        if len(text) > 22:
            text = text[:22] + '…'
        self.canvas.itemconfigure(self._label, text=text)

    def _update_text(self):
        if self._state == 'recording':
            text = 'Диктовка…'
        elif self._state == 'processing':
            text = 'Обработка…'
        else:
            text = self._message
        if len(text) > 18:
            text = text[:18] + '…'
        self.canvas.itemconfigure(self._label, text=text)