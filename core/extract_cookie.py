import subprocess
import time
import json
import pickle
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIE_PATH = os.path.join(BASE_DIR, '..', 'data', 'cookies', 'qtc_cookies.pkl')
CDP_URL = 'http://localhost:9222/json'

# Auto-detect Edge installation
_EDGE_PATHS = [
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
]
EDGE_EXE = None
for p in _EDGE_PATHS:
    if os.path.exists(p):
        EDGE_EXE = p
        break
if EDGE_EXE is None:
    EDGE_EXE = _EDGE_PATHS[0]  # fallback

def is_edge_cdp_running():
    """Check if Edge CDP port is already open."""
    import urllib.request
    try:
        with urllib.request.urlopen(CDP_URL, timeout=3) as resp:
            return True
    except Exception:
        return False

def launch_edge_with_cdp():
    """Launch Edge with remote debugging enabled."""
    print("Edge CDP not running. Launching Edge with --remote-debugging-port=9222 ...")
    subprocess.Popen([
        EDGE_EXE,
        '--remote-debugging-port=9222',
        '--remote-allow-origins=*',
        '--no-first-run',
        '--no-default-browser-check',
        'http://www.qtc.com.cn'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Wait for CDP to become available
    for i in range(20):
        time.sleep(0.5)
        if is_edge_cdp_running():
            print("Edge CDP is ready.")
            return True
    print("ERROR: Edge CDP failed to start within 10 seconds.")
    return False

def extract_cookies():
    """Extract cookies for qtc.com.cn via CDP."""
    import urllib.request
    import websocket

    if not is_edge_cdp_running():
        if not launch_edge_with_cdp():
            return None

    # Get the first page's WebSocket URL
    with urllib.request.urlopen(CDP_URL, timeout=10) as resp:
        pages = json.loads(resp.read().decode('utf-8'))

    qtc_pages = [p for p in pages if 'qtc.com.cn' in p.get('url', '')]
    if not qtc_pages:
        print("WARNING: No 量科网 page found in CDP. Using first available page.")
        qtc_pages = pages

    ws_url = qtc_pages[0]['webSocketDebuggerUrl']
    print(f"Connecting to CDP: {ws_url}")

    ws = websocket.create_connection(ws_url)
    ws.send(json.dumps({'id': 1, 'method': 'Network.getAllCookies'}))
    result = ws.recv()
    data = json.loads(result)
    ws.close()

    if 'result' not in data or 'cookies' not in data['result']:
        print("ERROR: Failed to get cookies from CDP.")
        return None

    cookies = data['result']['cookies']
    qtc_cookies = {c['name']: c['value'] for c in cookies if 'qtc.com.cn' in c.get('domain', '')}

    print(f"Extracted {len(qtc_cookies)} cookies for qtc.com.cn:")
    for name in qtc_cookies:
        print(f"  - {name}")

    # Save
    with open(COOKIE_PATH, 'wb') as f:
        pickle.dump(qtc_cookies, f)
    print(f"Cookies saved to: {COOKIE_PATH}")
    return qtc_cookies

if __name__ == '__main__':
    cookies = extract_cookies()
    if cookies:
        print("Cookie extraction completed successfully.")
        sys.exit(0)
    else:
        print("Cookie extraction failed.")
        sys.exit(1)
