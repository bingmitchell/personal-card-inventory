#!/usr/bin/env python3
"""
Card Inventory launcher.
Starts the Flask server, initializes the database, and opens the browser.

Run directly:   python launcher.py
Built with:     pyinstaller ../card_inventory.spec
"""
import sys
import os
import threading
import time
import webbrowser
from pathlib import Path

# When running as a PyInstaller bundle _MEIPASS is the temp extraction dir.
# When running from source it's the scripts/ directory.
BASE_DIR = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
os.chdir(str(BASE_DIR))

PORT = 8000


def _wait_and_open():
    time.sleep(2.0)
    webbrowser.open(f"http://localhost:{PORT}/form")


if __name__ == '__main__':
    from lib.db import init_db
    from forms import app

    init_db()

    t = threading.Thread(target=_wait_and_open, daemon=True)
    t.start()

    print(f"Card Inventory is running at http://localhost:{PORT}/form")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
