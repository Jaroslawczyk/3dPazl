"""Desktop app: API server in a background thread + native window (pywebview) with the 3D UI.

    python -m pazl            # window + server
    python -m pazl --browser  # server + open in the default browser instead of a window
"""
import sys
import threading
import time
import urllib.request

from .server.app import HOST, PORT, serve

URL = f"http://{HOST}:{PORT}/"


def _running() -> bool:
    try:
        urllib.request.urlopen(URL + "api/state", timeout=1)
        return True
    except Exception:
        return False


def main():
    if "--mcp" in sys.argv:  # installed exe: MCP stdio server for the in-app Claude Code chat
        from .mcp import main as mcp_main
        return mcp_main()
    if not _running():
        threading.Thread(target=serve, daemon=True).start()
        for _ in range(100):
            if _running():
                break
            time.sleep(0.1)
    if "--browser" in sys.argv:
        import webbrowser
        webbrowser.open(URL)
        while True:
            time.sleep(3600)
    import webview
    webview.create_window("3dPazl — конструктор зданий", URL, width=1500, height=920, min_size=(1000, 650))
    webview.start()


main()
