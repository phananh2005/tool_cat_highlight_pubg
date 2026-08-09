"""PUBG Highlight Cutter — Entry point."""
import sys
import os
import logging
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

stdout_utf8 = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(stdout_utf8),
        logging.FileHandler(Path(__file__).parent / "debug.log", encoding='utf-8')
    ]
)

print("[DEBUG] Starting PUBG Highlight Cutter...", flush=True)

try:
    print("[DEBUG] Importing PyQt6...", flush=True)
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont
    print("[DEBUG] PyQt6 imported OK", flush=True)

    print("[DEBUG] Importing MainWindow...", flush=True)
    from gui.main_window import MainWindow
    print("[DEBUG] MainWindow imported OK", flush=True)
except Exception as e:
    print(f"[ERROR] Import failed: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)


def main():
    try:
        print("[DEBUG] Creating QApplication...", flush=True)
        app = QApplication(sys.argv)
        app.setApplicationName("PUBG Highlight Cutter")
        app.setStyle("Fusion")

        font = QFont("Segoe UI", 10)
        app.setFont(font)

        print("[DEBUG] Creating MainWindow...", flush=True)
        window = MainWindow()
        print("[DEBUG] Showing window...", flush=True)
        window.show()
        print("[DEBUG] Starting event loop...", flush=True)
        ret = app.exec()
        print(f"[DEBUG] Event loop ended with code {ret}", flush=True)
        sys.exit(ret)
    except Exception as e:
        print(f"[ERROR] {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
