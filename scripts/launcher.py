#!/usr/bin/env python3
"""
Card Inventory launcher.
Starts the Flask server, initializes the database, and opens the browser.

Run directly:   python launcher.py
Built with:     python3 -m PyInstaller ../card_inventory.spec --noconfirm
"""
import sys
import os
import signal
import socket
import subprocess
import threading
import time
import webbrowser
from pathlib import Path

BASE_DIR = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
os.chdir(str(BASE_DIR))

PORT = 8000


def _kill_port(port):
    """Kill any process currently holding the given port."""
    try:
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True, text=True
        )
        for pid in result.stdout.strip().split('\n'):
            pid = pid.strip()
            if pid:
                os.kill(int(pid), signal.SIGTERM)
        time.sleep(0.5)
    except Exception:
        pass


def _wait_and_open():
    time.sleep(2.0)
    webbrowser.open(f"http://localhost:{PORT}/form")


if __name__ == '__main__':
    from lib.db import init_db
    from forms import app

    _kill_port(PORT)
    init_db()

    t = threading.Thread(target=_wait_and_open, daemon=True)
    t.start()

    print(f"Card Inventory running at http://localhost:{PORT}/form")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
