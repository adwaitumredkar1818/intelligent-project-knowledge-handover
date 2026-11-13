import asyncio
import json
import base64
import os
import subprocess
import time
import httpx
import websockets

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT = 9444
USER_DATA_DIR = os.path.join(os.environ.get("TEMP", r"C:\temp"), "edge_shot_data")
OUTPUT_DIR = r"C:\Users\ASUS\.gemini\antigravity\brain\02de4ae1-66bd-4199-a5d0-c58cccd3f673\screenshots"

os.makedirs(OUTPUT_DIR, exist_ok=True)

TARGETS = [
    {"name": "01_hero_to_problem.png", "scroll": 650, "w": 1280, "h": 900, "reduced": False},
    {"name": "02_problem_cards.png", "scroll": 950, "w": 1280, "h": 900, "reduced": False},
    {"name": "03_introducing_assembly.png", "scroll": 1650, "w": 1280, "h": 900, "reduced": False},
    {"name": "04_how_it_works.png", "scroll": 2400, "w": 1280, "h": 900, "reduced": False},
    {"name": "05_knowledge_intelligence.png", "scroll": 3250, "w": 1280, "h": 900, "reduced": False},
    {"name": "06_knowledge_explorer.png", "scroll": 4100, "w": 1280, "h": 900, "reduced": False},
    {"name": "07_structured_handovers.png", "scroll": 4900, "w": 1280, "h": 900, "reduced": False},
    {"name": "08_roles_continuity.png", "scroll": 5700, "w": 1280, "h": 900, "reduced": False},
    {"name": "09_final_cta.png", "scroll": 7300, "w": 1280, "h": 900, "reduced": False},
    {"name": "10_mobile_problem.png", "scroll": 800, "w": 390, "h": 844, "reduced": False},
    {"name": "11_reduced_motion_problem.png", "scroll": 950, "w": 1280, "h": 900, "reduced": True},
]


async def capture_item(client: httpx.AsyncClient, item: dict):
    out_path = os.path.join(OUTPUT_DIR, item["name"])
    target_url = "http://localhost:3001"

    # Create new blank tab
    res = await client.put(f"http://127.0.0.1:{PORT}/json/new?about:blank")
    tab = res.json()
    ws_url = tab["webSocketDebuggerUrl"]
    tab_id = tab["id"]

    try:
        async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
            # Enable Page domain
            await ws.send(json.dumps({"id": 1, "method": "Page.enable"}))
            await ws.recv()

            # Bypass intro animation overlay in this session
            await ws.send(json.dumps({
                "id": 2,
                "method": "Page.addScriptToEvaluateOnNewDocument",
                "params": {"source": "try { sessionStorage.setItem('handover_intro_seen', '1'); } catch(e){}"}
            }))
            await ws.recv()

            # Viewport override
            await ws.send(json.dumps({
                "id": 3,
                "method": "Emulation.setDeviceMetricsOverride",
                "params": {
                    "width": item["w"],
                    "height": item["h"],
                    "deviceScaleFactor": 2,
                    "mobile": item["w"] < 768
                }
            }))
            await ws.recv()

            if item["reduced"]:
                await ws.send(json.dumps({
                    "id": 4,
                    "method": "Emulation.setEmulatedMedia",
                    "params": {"features": [{"name": "prefers-reduced-motion", "value": "reduce"}]}
                }))
                await ws.recv()

            # Navigate to target
            await ws.send(json.dumps({
                "id": 5,
                "method": "Page.navigate",
                "params": {"url": target_url}
            }))
            await ws.recv()

            # Wait for page load and initial hydration
            await asyncio.sleep(2.5)

            # Scroll to target position
            if item["scroll"] > 0:
                await ws.send(json.dumps({
                    "id": 6,
                    "method": "Runtime.evaluate",
                    "params": {"expression": f"window.scrollTo({{ top: {item['scroll']}, behavior: 'instant' }});"}
                }))
                await ws.recv()
                # Wait for scroll-aware section dividers and animations
                await asyncio.sleep(1.5)

            # Capture screenshot
            await ws.send(json.dumps({
                "id": 7,
                "method": "Page.captureScreenshot",
                "params": {"format": "png"}
            }))

            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                if data.get("id") == 7:
                    png_data = base64.b64decode(data["result"]["data"])
                    with open(out_path, "wb") as f:
                        f.write(png_data)
                    print(f"[OK] {item['name']} ({len(png_data):,} bytes)")
                    break
    finally:
        try:
            await client.get(f"http://127.0.0.1:{PORT}/json/close/{tab_id}")
        except Exception:
            pass


async def main():
    print(f"Launching Edge on port {PORT}...")
    edge_proc = subprocess.Popen([
        EDGE_PATH,
        "--headless=new",
        f"--remote-debugging-port={PORT}",
        f"--user-data-dir={USER_DATA_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1280,900"
    ])

    try:
        # Wait for Edge ready
        async with httpx.AsyncClient() as client:
            ready = False
            for _ in range(20):
                await asyncio.sleep(0.3)
                try:
                    r = await client.get(f"http://127.0.0.1:{PORT}/json/version")
                    if r.status_code == 200:
                        ready = True
                        break
                except Exception:
                    pass

            if not ready:
                print("Failed to connect to Edge debugger")
                return

            print(f"Edge ready! Capturing {len(TARGETS)} screenshots...")
            for item in TARGETS:
                try:
                    await capture_item(client, item)
                except Exception as e:
                    print(f"[FAIL] {item['name']}: {e}")

    finally:
        edge_proc.terminate()
        try:
            edge_proc.wait(timeout=3)
        except Exception:
            edge_proc.kill()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
