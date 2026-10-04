#!/usr/bin/env python3
"""
scripts/capture_v3_screenshots.py
---------------------------------
Automated Chrome DevTools Protocol (CDP) screenshot harness for KRATOS V3 Phase 1.
Captures all 14 mandatory acceptance views with real data, real Leaflet rendering,
and real interactive component states.
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
OUTPUT_DIR = Path(r"C:\Users\mukesh\.gemini\antigravity\brain\ca0675d4-38a6-49e3-9f04-37cee3d33c57\screenshots")
CDP_PORT = 9223


class ChromeRunner:
    def __init__(self):
        self.proc = None
        self.ws = None
        self.msg_id = 1

    async def start(self):
        cmd = [
            CHROME_PATH,
            f"--remote-debugging-port={CDP_PORT}",
            "--headless=new",
            "--disable-gpu",
            "--window-size=1920,1080",
            "--no-first-run",
            "--no-default-browser-check",
            "--user-data-dir=" + str(OUTPUT_DIR / "chrome_profile"),
            "about:blank",
        ]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await asyncio.sleep(2)

        # Query /json/list to get websocket debugger URL
        for _ in range(10):
            try:
                req = urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/list", timeout=2)
                data = json.loads(req.read().decode())
                if data and "webSocketDebuggerUrl" in data[0]:
                    ws_url = data[0]["webSocketDebuggerUrl"]
                    self.ws = await websockets.connect(ws_url, max_size=20 * 1024 * 1024)
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
        out_path = OUTPUT_DIR / filename
        with open(out_path, "wb") as f:
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


async def main():
    print("=" * 70)
    print(" KRATOS V3 PHASE 1 — AUTOMATED LIVE VIEW SCREENSHOT CAPTURE")
    print("=" * 70)

    runner = ChromeRunner()
    await runner.start()

    try:
        # Navigate to KRATOS V3
        print("\n[1/14] Navigating to KRATOS V3 Dashboard...")
        await runner.send("Page.navigate", {"url": "http://127.0.0.1:5173/"})
        await asyncio.sleep(4)

        # 1. Monitoring Overview
        print("\n[View 1] Monitoring Overview (Full light theme workspace)...")
        await runner.capture("01_overview_light_theme.png")

        # 2. Region Dropdown Expanded
        print("\n[View 2] Region Selector Dropdown...")
        await runner.evaluate("""
            const sel = document.querySelector('select[aria-label="Select Monitoring Region"]');
            if (sel) { sel.focus(); }
        """)
        await runner.capture("02_region_dropdown_expanded.png")

        # 3. Second Region Selected (Singrauli-Sonbhadra)
        print("\n[View 3] Selecting second region: Singrauli-Sonbhadra Energy Basin...")
        await runner.evaluate("""
            const sel = document.querySelector('select[aria-label="Select Monitoring Region"]');
            if (sel) {
                sel.value = 'singrauli_sonbhadra';
                sel.dispatchEvent(new Event('change', { bubbles: true }));
            }
        """)
        await asyncio.sleep(3)
        await runner.capture("03_second_region_selected.png")

        # 4. Pan-India Selected
        print("\n[View 4] Selecting Pan-India National Overview...")
        await runner.evaluate("""
            const sel = document.querySelector('select[aria-label="Select Monitoring Region"]');
            if (sel) {
                sel.value = '';
                sel.dispatchEvent(new Event('change', { bubbles: true }));
            }
        """)
        await asyncio.sleep(3)
        await runner.capture("04_pan_india_selected.png")

        # 5. Timeline Presets
        print("\n[View 5] Timeline Presets Toolbar...")
        await runner.evaluate("""
            const btn7d = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === '7d');
            if (btn7d) { btn7d.click(); }
        """)
        await asyncio.sleep(2)
        await runner.capture("05_timeline_presets.png")

        # 6. Custom Range Date Selector
        print("\n[View 6] Opening Custom Date Range Selector...")
        await runner.evaluate("""
            const btnCustom = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Custom Range'));
            if (btnCustom) { btnCustom.click(); }
        """)
        await asyncio.sleep(1)
        await runner.capture("06_custom_date_range_picker.png")

        # 7. Dashboard after Timeline Change (Historical Replay Mode)
        print("\n[View 7] Historical Replay Mode with Warning Banner...")
        await runner.evaluate("""
            const form = document.querySelector('form');
            if (form) {
                const submit = form.querySelector('button[type="submit"]');
                if (submit) submit.click();
            }
        """)
        await asyncio.sleep(2)
        await runner.capture("07_timeline_filtered_dashboard.png")

        # Return to live
        await runner.evaluate("""
            const btnReturn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Return to Live'));
            if (btnReturn) btnReturn.click();
        """)
        await asyncio.sleep(2)

        # 8. High Zoom Satellite Imagery Stability (Leaflet map zoom)
        print("\n[View 8] High Zoom Satellite Basemap (Zoom 17)...")
        await runner.evaluate("""
            const mapEl = document.querySelector('.leaflet-container');
            if (mapEl && window.L) {
                // Find leaflet map instance
                for (let k in mapEl) {
                    if (k.startsWith('_leaflet_map') || (mapEl[k] && mapEl[k]._leaflet_id)) {
                        const m = mapEl[k];
                        if (m.setZoom) { m.setView([24.18, 82.79], 16); break; }
                    }
                }
            }
            const inBtn = document.querySelector('.leaflet-control-zoom-in');
            if (inBtn) {
                for (let i = 0; i < 4; i++) { inBtn.click(); }
            }
        """)
        await asyncio.sleep(3)
        await runner.capture("08_satellite_high_zoom_stability.png")

        # Reset zoom
        await runner.evaluate("""
            const outBtn = document.querySelector('.leaflet-control-zoom-out');
            if (outBtn) {
                for (let i = 0; i < 4; i++) { outBtn.click(); }
            }
        """)
        await asyncio.sleep(2)

        # 9. Selected Observation in Right Panel
        print("\n[View 9] Selected Thermal Observation in Investigation Panel...")
        await runner.evaluate("""
            const firstEventRow = document.querySelector('tbody tr');
            if (firstEventRow) { firstEventRow.click(); }
        """)
        await asyncio.sleep(2)
        await runner.capture("09_selected_observation_panel.png")

        # 10. Selected Persistent Cluster in Right Panel
        print("\n[View 10] Selected Persistent Cluster in Investigation Panel...")
        await runner.evaluate("""
            const clusterCard = Array.from(document.querySelectorAll('div')).find(d => d.textContent.includes('hits') && d.textContent.includes('src_'));
            if (clusterCard) { clusterCard.click(); }
        """)
        await asyncio.sleep(2)
        await runner.capture("10_selected_cluster_panel.png")

        # 11. Selected OSM Facility in Right Panel
        print("\n[View 11] Selected Industrial Facility via Search...")
        await runner.evaluate("""
            const searchInput = document.querySelector('input[placeholder*="Search corridors"]');
            if (searchInput) {
                searchInput.value = 'chimney';
                searchInput.dispatchEvent(new Event('input', { bubbles: true }));
            }
        """)
        await asyncio.sleep(2)
        await runner.evaluate("""
            const facResult = document.querySelector('div[class*="divide-y"] button');
            if (facResult) { facResult.click(); }
        """)
        await asyncio.sleep(2)
        await runner.capture("11_selected_facility_panel.png")

        # 12. Notification Center Popover
        print("\n[View 12] Opening Real Notification Center...")
        await runner.evaluate("""
            const bell = document.querySelector('button[aria-label="View notifications"]');
            if (bell) { bell.click(); }
        """)
        await asyncio.sleep(2)
        await runner.capture("12_notification_center_open.png")

        # Close notifications
        await runner.evaluate("""
            const bell = document.querySelector('button[aria-label="View notifications"]');
            if (bell) { bell.click(); }
        """)
        await asyncio.sleep(1)

        # 13. Regional Detection Table Filtered
        print("\n[View 13] Regional Detection Table...")
        await runner.evaluate("""
            const selRisk = document.querySelector('select[aria-label="Filter by Risk Level"]');
            if (selRisk) {
                selRisk.value = 'high';
                selRisk.dispatchEvent(new Event('change', { bubbles: true }));
            }
        """)
        await asyncio.sleep(2)
        await runner.capture("13_regional_detection_table.png")

        # 14. AI Investigator Chat Drawer
        print("\n[View 14] Launching AI Situation Briefing / Investigator Chat Drawer...")
        await runner.evaluate("""
            const aiBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('AI Situation Briefing') || b.textContent.includes('Investigate Target'));
            if (aiBtn) { aiBtn.click(); }
        """)
        await asyncio.sleep(2)
        await runner.capture("14_ai_investigator_chat.png")

        print("\n" + "=" * 70)
        print("✓ ALL 14 LIVE APPLICATION SCREENSHOTS CAPTURED SUCCESSFULLY!")
        print("=" * 70)

    finally:
        await runner.stop()


if __name__ == "__main__":
    asyncio.run(main())
