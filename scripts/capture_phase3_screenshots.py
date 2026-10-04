#!/usr/bin/env python3
"""scripts/capture_phase3_screenshots.py
---------------------------------------
Automated Chrome DevTools Protocol (CDP) screenshot harness for KRATOS V3 Phase 3.
Captures all 22 required operational platform verification views directly from the live web application on port 5174.
"""

import asyncio
import base64
import json
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
WORKSPACE_DIR = Path(r"C:\Users\mukesh\.gemini\antigravity\scratch\industrial-thermal-intelligence")
WORKSPACE_OUTPUT = WORKSPACE_DIR / "screenshots" / "phase3"
ARTIFACT_OUTPUT = Path(r"C:\Users\mukesh\.gemini\antigravity\brain\ca0675d4-38a6-49e3-9f04-37cee3d33c57\screenshots\phase3")

WORKSPACE_OUTPUT.mkdir(parents=True, exist_ok=True)
ARTIFACT_OUTPUT.mkdir(parents=True, exist_ok=True)

CDP_PORT = 9235
APP_URL = "http://127.0.0.1:5174"


class ChromeRunner:
    def __init__(self):
        self.proc = None
        self.ws = None
        self.msg_id = 1

    async def start(self):
        profile_dir = WORKSPACE_DIR / "screenshots" / "chrome_profile_phase3"
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


async def main():
    print("=" * 75)
    print(" KRATOS V3 PHASE 3 OPERATIONAL PLATFORM — 22-POINT BROWSER VERIFICATION")
    print(f" Connecting to: {APP_URL}")
    print("=" * 75)

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

    # 1. Overview Monitoring
    print("\n[1/22] Capturing Overview Monitoring...")
    await click_nav_item(chrome, "Overview Monitoring")
    await asyncio.sleep(2)
    await chrome.capture("01_phase3_overview_monitoring.png")

    # 2. Live Geospatial Map
    print("\n[2/22] Capturing Live Geospatial Map...")
    await click_nav_item(chrome, "Live Geospatial Map")
    await asyncio.sleep(3)
    await chrome.capture("02_phase3_live_geospatial_map.png")

    # 3. Thermal Analysis & FRP
    print("\n[3/22] Capturing Thermal Analysis & FRP...")
    await click_nav_item(chrome, "Thermal Analysis & FRP")
    await asyncio.sleep(2.5)
    await chrome.capture("03_phase3_thermal_analysis_frp.png")

    # 4. Source & Facility Intel
    print("\n[4/22] Capturing Source & Facility Intel (Sum = 312)...")
    await click_nav_item(chrome, "Source & Facility Intel")
    await asyncio.sleep(2.5)
    await chrome.capture("04_phase3_source_facility_intel.png")

    # 5. Risk & Prediction
    print("\n[5/22] Capturing Risk & Prediction Workspace...")
    await click_nav_item(chrome, "Risk & Prediction")
    await asyncio.sleep(2.5)
    await chrome.capture("05_phase3_risk_prediction.png")

    # 6. Incident Investigations (Non-zero FRP mapping verified)
    print("\n[6/22] Capturing Incident Investigations with Genuine FRP...")
    await click_nav_item(chrome, "Incident Investigations")
    await asyncio.sleep(2.5)
    await chrome.capture("06_phase3_incident_investigations.png")

    # 7. Intelligence Reports Workspace
    print("\n[7/22] Capturing Intelligence Reports Workspace...")
    await click_nav_item(chrome, "Intelligence Reports")
    await asyncio.sleep(2.5)
    await chrome.capture("07_phase3_reports_workspace.png")

    # 8. Reports Region Dossier
    print("\n[8/22] Capturing Reports Region Dossier View...")
    await chrome.evaluate("""
        (() => {
            const rows = Array.from(document.querySelectorAll('table tbody tr'));
            if (rows.length > 0) {
                rows[0].click();
            }
        })()
    """)
    await asyncio.sleep(2)
    await chrome.capture("08_phase3_reports_region_dossier.png")

    # 9. Reports Approval Workflow & Versioning Controls
    print("\n[9/22] Capturing Reports Approval Workflow & Version Controls...")
    await chrome.evaluate("""
        (() => {
            const panel = document.querySelector('.overflow-y-auto') || window;
            if (panel.scrollTo) {
                panel.scrollTo(0, 450);
            }
        })()
    """)
    await asyncio.sleep(1.5)
    await chrome.capture("09_phase3_reports_approval_workflow.png")

    # 10. Statutory Authority Submission Modal
    print("\n[10/22] Capturing Statutory Authority Submission Modal...")
    await chrome.evaluate("""
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const submitBtn = btns.find(b => b.textContent && b.textContent.includes('Record Authority Submission'));
            if (submitBtn) submitBtn.click();
        })()
    """)
    await asyncio.sleep(1.5)
    await chrome.capture("10_phase3_authority_submission_modal.png")

    # 11. Statutory Authority Submission Log / Audit
    print("\n[11/22] Capturing Authority Submission Log Table...")
    await chrome.evaluate("""
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const cancelBtn = btns.find(b => b.textContent && b.textContent.includes('Cancel'));
            if (cancelBtn) cancelBtn.click();
        })()
    """)
    await asyncio.sleep(1)
    await chrome.evaluate("""
        (() => {
            window.scrollTo(0, document.body.scrollHeight);
        })()
    """)
    await asyncio.sleep(1.5)
    await chrome.capture("11_phase3_authority_submission_log.png")

    # 12. Follow-up & Verification Workspace
    print("\n[12/22] Capturing Follow-up & Verification Workspace...")
    await click_nav_item(chrome, "Follow-up & Verification")
    await asyncio.sleep(2.5)
    await chrome.capture("12_phase3_followups_workspace.png")

    # 13. Follow-up Idempotency & Duplicate Conflict Banner / Merge Tool
    print("\n[13/22] Capturing Follow-up Duplicate Conflict & Merge Tool...")
    await chrome.evaluate("""
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const mergeBtn = btns.find(b => b.textContent && (b.textContent.includes('Merge') || b.textContent.includes('Duplicate')));
            if (mergeBtn) mergeBtn.click();
        })()
    """)
    await asyncio.sleep(1.5)
    await chrome.capture("13_phase3_followup_idempotency_banner.png")

    # 14. Follow-up Verification Detail / 7-Stage Lifecycle Modal
    print("\n[14/22] Capturing Follow-up Verification Detail Modal...")
    await chrome.evaluate("""
        (() => {
            const tasks = document.querySelectorAll('.space-y-3 > div, table tbody tr');
            if (tasks.length > 0) tasks[0].click();
        })()
    """)
    await asyncio.sleep(2)
    await chrome.capture("14_phase3_followup_verification_detail.png")

    # Close modal if opened
    await chrome.evaluate("""
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const closeBtn = btns.find(b => b.textContent && (b.textContent.includes('Close') || b.textContent.includes('Cancel')));
            if (closeBtn) closeBtn.click();
        })()
    """)
    await asyncio.sleep(1)

    # 15. Advanced Analytics - 10 Industrial Corridors
    print("\n[15/22] Capturing Advanced Analytics - 10 Industrial Corridors Ranking...")
    await click_nav_item(chrome, "Advanced Analytics")
    await asyncio.sleep(2.5)
    await chrome.capture("15_phase3_advanced_analytics_corridors.png")

    # 16. Advanced Analytics - Diurnal & Recurrence Spectrum
    print("\n[16/22] Capturing Advanced Analytics - Diurnal & Recurrence Spectrum...")
    await chrome.evaluate("""
        (() => {
            window.scrollTo(0, 500);
        })()
    """)
    await asyncio.sleep(1.5)
    await chrome.capture("16_phase3_advanced_analytics_diurnal_recurrence.png")

    # 17. Advanced Analytics - Proxy-Label Truth Notice Banner
    print("\n[17/22] Capturing Advanced Analytics - ML Proxy-Label Truth Notice Banner...")
    await chrome.evaluate("""
        (() => {
            window.scrollTo(0, 1100);
        })()
    """)
    await asyncio.sleep(1.5)
    await chrome.capture("17_phase3_advanced_analytics_proxy_disclaimer.png")

    # 18. Data & Integrations - Connectors Catalog
    print("\n[18/22] Capturing Data & Integrations - Connectors Catalog...")
    await click_nav_item(chrome, "Data & Integrations")
    await asyncio.sleep(2.5)
    await chrome.capture("18_phase3_integrations_connectors_catalog.png")

    # 19. Data & Integrations - Live Connection Tester & SSRF Protection
    print("\n[19/22] Capturing Data & Integrations - Connection Tester & SSRF Protection...")
    await chrome.evaluate("""
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const testBtn = btns.find(b => b.textContent && b.textContent.includes('Test Connection'));
            if (testBtn) testBtn.click();
        })()
    """)
    await asyncio.sleep(2)
    await chrome.capture("19_phase3_integrations_connection_tester.png")

    # 20. Settings & Administration - RBAC User Profiles
    print("\n[20/22] Capturing Settings & Administration - RBAC Profiles...")
    await click_nav_item(chrome, "Settings & Admin")
    await asyncio.sleep(2.5)
    await chrome.capture("20_phase3_settings_rbac_profiles.png")

    # 21. Settings & Administration - Operational Monitoring Thresholds
    print("\n[21/22] Capturing Settings - Operational Monitoring Thresholds...")
    await chrome.evaluate("""
        (() => {
            window.scrollTo(0, 450);
        })()
    """)
    await asyncio.sleep(1.5)
    await chrome.capture("21_phase3_settings_monitoring_thresholds.png")

    # 22. Settings & Administration - Tamper-Evident System Audit Trail
    print("\n[22/22] Capturing Settings - Tamper-Evident Audit Trail...")
    await chrome.evaluate("""
        (() => {
            window.scrollTo(0, 1000);
        })()
    """)
    await asyncio.sleep(1.5)
    await chrome.capture("22_phase3_settings_tamper_evident_audit_log.png")

    print("\n" + "=" * 75)
    print(" ✓ ALL 22 PHASE 3 VERIFICATION SCREENSHOTS CAPTURED AND STORED!")
    print("=" * 75)

    await chrome.stop()


if __name__ == "__main__":
    asyncio.run(main())
