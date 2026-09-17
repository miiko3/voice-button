import ctypes
import os
import sys
import time
import traceback

from voicebutton.app import VoiceButtonApp

MUTEX_NAME = 'Local\\VoiceButtonSingleton'


def _single_instance():
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == 183:
        return False
    return True


def main():
    if not _single_instance():
        return
    try:
        app = VoiceButtonApp()
        app.capsule.run()
    except Exception:
        log_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'VoiceButton')
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, 'error.log')
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(time.strftime('%Y-%m-%d %H:%M:%S') + '\n')
            f.write(traceback.format_exc())
            f.write('\n')
        try:
            ctypes.windll.user32.MessageBoxW(0, 'Ошибка запуска Voice Button.', 'Voice Button', 0x10)
        except Exception:
            pass


if __name__ == '__main__':
    main()