#!/usr/bin/env python3
"""scripts/capture_enhancement_phase1_screenshots.py
--------------------------------------------------
Automated Chrome DevTools Protocol (CDP) screenshot harness for KRATOS V3.1 Enhancement Phase 1.
Captures all 20 required verification views directly from the live web application on port 5174/5173.
"""

import asyncio
import base64
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
WORKSPACE_DIR = Path(r"C:\Users\mukesh\.gemini\antigravity\scratch\industrial-thermal-intelligence")
WORKSPACE_OUTPUT = WORKSPACE_DIR / "screenshots" / "enhancement_phase1"
ARTIFACT_OUTPUT = Path(r"C:\Users\mukesh\.gemini\antigravity\brain\ca0675d4-38a6-49e3-9f04-37cee3d33c57\screenshots\enhancement_phase1")

WORKSPACE_OUTPUT.mkdir(parents=True, exist_ok=True)
ARTIFACT_OUTPUT.mkdir(parents=True, exist_ok=True)

CDP_PORT = 9238
APP_URL = "http://127.0.0.1:5174"


class ChromeRunner:
    def __init__(self):
        self.proc = None
        self.ws = None
        self.msg_id = 1

    async def start(self):
        profile_dir = WORKSPACE_DIR / "screenshots" / "chrome_profile_enh1"
        profile_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            CHROME_PATH,
            f"--remote-debugging-port={CDP_PORT}",
            "--headless=new",
            "--disable-gpu",
            "--window-size=1920,1080",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={profile_dir}",
            "about:blank",
        ]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await asyncio.sleep(2)

        for _ in range(15):
            try:
                req = urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/list", timeout=2)
                data = json.loads(req.read().decode())
                if data and "webSocketDebuggerUrl" in data[0]:
                    ws_url = data[0]["webSocketDebuggerUrl"]
                    self.ws = await websockets.connect(ws_url, max_size=30 * 1024 * 1024)
                    return
            except Exception:
                await asyncio.sleep(1)
        raise RuntimeError("Failed to connect to Chrome CDP WebSocket")

    async def send(self, method, params=None):
        mid = self.msg_id
        self.msg_id += 1
        payload = {"id": mid, "method": method, "params": params or {}}
        await self.ws.send(json.dumps(payload))
        while True:
            resp = json.loads(await self.ws.recv())
            if resp.get("id") == mid:
                if "error" in resp:
                    raise RuntimeError(f"CDP error: {resp['error']}")
                return resp.get("result", {})

    async def evaluate(self, expr):
        res = await self.send("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": True,
        })
        return res.get("result", {}).get("value")

    async def capture(self, filename: str):
        res = await self.send("Page.captureScreenshot", {"format": "png"})
        data = base64.b64decode(res["data"])

        # Save to workspace output
        ws_path = WORKSPACE_OUTPUT / filename
        with open(ws_path, "wb") as f:
            f.write(data)

        # Save to artifact output
        art_path = ARTIFACT_OUTPUT / filename
        with open(art_path, "wb") as f:
            f.write(data)

        print(f"      ✓ Captured {filename} ({len(data):,} bytes)")

    async def stop(self):
        if self.ws:
            await self.ws.close()
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except Exception:
                self.proc.kill()


async def click_nav_item(chrome, text_match: str):
    return await chrome.evaluate(f"""
        (() => {{
            const aside = document.querySelector('aside');
            if (!aside) return false;
            const btns = Array.from(aside.querySelectorAll('button'));
            const target = btns.find(b => (b.innerText || b.textContent || '').includes('{text_match}'));
            if (target) {{
                target.click();
                return true;
            }}
            return false;
        }})()
    """)


async def click_timeline_preset(chrome, preset_label: str):
    return await chrome.evaluate(f"""
        (() => {{
            const btns = Array.from(document.querySelectorAll('button'));
            const target = btns.find(b => (b.innerText || b.textContent || '').trim() === '{preset_label}');
            if (target) {{
                target.click();
                return true;
            }}
            return false;
        }})()
    """)


async def main():
    print("=" * 80)
    print(" KRATOS V3.1 ENHANCEMENT PHASE 1 — 20-POINT LIVE BROWSER VERIFICATION")
    print(f" Target Application URL: {APP_URL}")
    print("=" * 80)

    chrome = ChromeRunner()
    await chrome.start()
    print("      ✓ Chrome headless instance connected via CDP on port", CDP_PORT)

    await chrome.send("Page.enable")
    await chrome.send("DOM.enable")
    await chrome.send("Network.enable")

    # Navigate to application
    print(f"\n[INIT] Loading Application at {APP_URL}...")
    await chrome.send("Page.navigate", {"url": APP_URL})
    await asyncio.sleep(4)

    # 1. 24h Timeline Live Telemetry
    print("\n[1/20] Capturing Monitoring Dashboard with 24h Timeline Preset...")
    await click_timeline_preset(chrome, "24h")
    await asyncio.sleep(2.5)
    await chrome.capture("01_dashboard_live_telemetry_24h.png")

    # 2. 7d Timeline Live Telemetry
    print("\n[2/20] Capturing Monitoring Dashboard with 7d Timeline Preset...")
    await click_timeline_preset(chrome, "7d")
    await asyncio.sleep(2.5)
    await chrome.capture("02_dashboard_live_telemetry_7d.png")

    # 3. 30d Timeline Live Telemetry
    print("\n[3/20] Capturing Monitoring Dashboard with 30d Timeline Preset...")
    await click_timeline_preset(chrome, "30d")
    await asyncio.sleep(2.5)
    await chrome.capture("03_dashboard_live_telemetry_30d.png")

    # 4. Target Investigation Overview (Select target)
    print("\n[4/20] Capturing Target Investigation Panel (Overview Tab)...")
    await chrome.evaluate("""
        (() => {
            const rows = Array.from(document.querySelectorAll('table tbody tr'));
            if (rows.length > 0) {
                rows[0].click();
            }
        })()
    """)
    await asyncio.sleep(2.5)
    await chrome.capture("04_target_investigation_overview.png")

    # 5. Target Investigation Metrics Tab
    print("\n[5/20] Capturing Target Investigation Panel (Metrics Tab)...")
    await chrome.evaluate("""
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const tabBtn = btns.find(b => (b.innerText || b.textContent || '').includes('Metrics'));
            if (tabBtn) tabBtn.click();
        })()
    """)
    await asyncio.sleep(1.5)
    await chrome.capture("05_target_investigation_metrics.png")

    # 6. Target Investigation Facility Tab
    print("\n[6/20] Capturing Target Investigation Panel (Facility Tab)...")
    await chrome.evaluate("""
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const tabBtn = btns.find(b => (b.innerText || b.textContent || '').includes('Facility'));
            if (tabBtn) tabBtn.click();
        })()
    """)
    await asyncio.sleep(1.5)
    await chrome.capture("06_target_investigation_facility.png")

    # 7. Target Investigation Audit Tab
    print("\n[7/20] Capturing Target Investigation Panel (Audit Tab)...")
    await chrome.evaluate("""
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const tabBtn = btns.find(b => (b.innerText || b.textContent || '').includes('Audit'));
            if (tabBtn) tabBtn.click();
        })()
    """)
    await asyncio.sleep(1.5)
    await chrome.capture("07_target_investigation_audit.png")

    # 8. Multi-Basemap: Satellite
    print("\n[8/20] Capturing Satellite World Imagery Basemap...")
    await chrome.evaluate("""
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const satBtn = btns.find(b => (b.innerText || b.textContent || '').includes('Satellite'));
            if (satBtn) satBtn.click();
        })()
    """)
    await asyncio.sleep(2)
    await chrome.capture("08_map_multibasemap_satellite.png")

    # 9. Multi-Basemap: Terrain
    print("\n[9/20] Capturing Terrain Topographic Basemap...")
    await chrome.evaluate("""
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const terrBtn = btns.find(b => (b.innerText || b.textContent || '').includes('Terrain'));
            if (terrBtn) terrBtn.click();
        })()
    """)
    await asyncio.sleep(2)
    await chrome.capture("09_map_multibasemap_terrain.png")

    # Switch back to Satellite
    await chrome.evaluate("""
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const satBtn = btns.find(b => (b.innerText || b.textContent || '').includes('Satellite'));
            if (satBtn) satBtn.click();
        })()
    """)
    await asyncio.sleep(1)

    # 10. Map Marker Selection & Panes
    print("\n[10/20] Capturing Map Marker Selection & High-Z Panes...")
    await chrome.evaluate("""
        (() => {
            // Trigger zoom to target
            if (window.__kratos_zoom_to__) {
                window.__kratos_zoom_to__(15.2, 76.66, 14);
            }
        })()
    """)
    await asyncio.sleep(2)
    await chrome.capture("10_map_marker_selection_panes.png")

    # 11. Detection Table Navigation
    print("\n[11/20] Capturing Detection Table Navigation...")
    await chrome.evaluate("""
        (() => {
            const table = document.querySelector('table');
            if (table) table.scrollIntoView({ behavior: 'smooth', block: 'center' });
        })()
    """)
    await asyncio.sleep(1.5)
    await chrome.capture("11_detection_table_navigation.png")

    # Scroll back to top
    await chrome.evaluate("window.scrollTo(0, 0)")
    await asyncio.sleep(0.5)

    # 12. AI Investigator Chat Stream
    print("\n[12/20] Capturing AI Investigator Chat Drawer & Stream...")
    await chrome.evaluate("""
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const aiBtn = btns.find(b => (b.innerText || b.textContent || '').includes('Ask AI to Investigate Target'));
            if (aiBtn) aiBtn.click();
        })()
    """)
    await asyncio.sleep(3.5)
    await chrome.capture("12_ai_investigator_chat_stream.png")

    # Close AI Chat Drawer
    await chrome.evaluate("""
        (() => {
            const closeBtn = document.querySelector('button[title="Close Drawer"]') || document.querySelector('aside button');
            if (closeBtn) closeBtn.click();
        })()
    """)
    await asyncio.sleep(1)

    # 13. Notification Center Real Alerts
    print("\n[13/20] Capturing Notification Center with Real Alerts...")
    await chrome.evaluate("""
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const bell = btns.find(b => b.querySelector('svg.lucide-bell') || (b.getAttribute('aria-label') || '').includes('notification'));
            if (bell) bell.click();
        })()
    """)
    await asyncio.sleep(2)
    await chrome.capture("13_notification_center_real_alerts.png")

    # Close Notification Center
    await chrome.evaluate("""
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const bell = btns.find(b => b.querySelector('svg.lucide-bell') || (b.getAttribute('aria-label') || '').includes('notification'));
            if (bell) bell.click();
        })()
    """)
    await asyncio.sleep(1)

    # 14. Global Search Target Fly-to
    print("\n[14/20] Capturing Global Search Target Fly-to...")
    await chrome.evaluate("""
        (() => {
            const input = document.querySelector('input[placeholder*="Search"]') || document.querySelector('header input');
            if (input) {
                input.focus();
                input.value = "Toranagallu";
                input.dispatchEvent(new Event('input', { bubbles: true }));
            }
        })()
    """)
    await asyncio.sleep(2)
    await chrome.capture("14_global_search_target_flyto.png")

    # 15. Workspace: Pan-India Map
    print("\n[15/20] Capturing Workspace 2: Pan-India Satellite Surveillance...")
    await click_nav_item(chrome, "Live Geospatial Map")
    await asyncio.sleep(3)
    await chrome.capture("15_workspace_pan_india.png")

    # 16. Workspace: Thermal Analysis & FRP
    print("\n[16/20] Capturing Workspace 3: Thermal Analysis & FRP...")
    await click_nav_item(chrome, "Thermal Analysis & FRP")
    await asyncio.sleep(2.5)
    await chrome.capture("16_workspace_thermal_analysis.png")

    # 17. Workspace: Source & Facility Intel
    print("\n[17/20] Capturing Workspace 4: Source & Facility Intel...")
    await click_nav_item(chrome, "Source & Facility Intel")
    await asyncio.sleep(2.5)
    await chrome.capture("17_workspace_source_facility.png")

    # 18. Workspace: Risk Prediction
    print("\n[18/20] Capturing Workspace 5: Risk & Prediction...")
    await click_nav_item(chrome, "Risk & Prediction")
    await asyncio.sleep(2.5)
    await chrome.capture("18_workspace_risk_prediction.png")

    # 19. Workspace: Incident Investigations
    print("\n[19/20] Capturing Workspace 6: Incident Investigations...")
    await click_nav_item(chrome, "Incident Investigations")
    await asyncio.sleep(2.5)
    await chrome.capture("19_workspace_investigations.png")

    # 20. Workspace: Reports & Follow-ups
    print("\n[20/20] Capturing Workspace 7: Intelligence Reports Workspace...")
    await click_nav_item(chrome, "Intelligence Reports")
    await asyncio.sleep(2.5)
    await chrome.capture("20_workspace_reports_and_followups.png")

    print("\n" + "=" * 80)
    print(" ALL 20 ENHANCEMENT PHASE 1 VERIFICATION SCREENSHOTS CAPTURED SUCCESSFULLY!")
    print(f" Workspace Output: {WORKSPACE_OUTPUT}")
    print(f" Artifact Output:  {ARTIFACT_OUTPUT}")
    print("=" * 80)

    await chrome.stop()


if __name__ == "__main__":
    asyncio.run(main())
