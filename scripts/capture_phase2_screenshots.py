#!/usr/bin/env python3
"""
scripts/capture_phase2_screenshots.py
-------------------------------------
Automated Chrome DevTools Protocol (CDP) screenshot harness for KRATOS V3 Phase 2.
Captures all required Phase 2 intelligence workspaces, facility profiles, FRP analytics,
explainable risk priority queues, investigations workflow, and AI investigator chat.
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
CDP_PORT = 9224  # use dedicated port 9224 to avoid collision


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
            "--user-data-dir=" + str(OUTPUT_DIR / "chrome_profile_phase2"),
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
                    self.ws = await websockets.connect(ws_url, max_size=25 * 1024 * 1024)
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
    print(" KRATOS V3 PHASE 2 — AUTOMATED LIVE VIEW SCREENSHOT CAPTURE")
    print("=" * 70)

    runner = ChromeRunner()
    await runner.start()

    try:
        # Navigate to KRATOS V3
        print("\n[1/11] Navigating to KRATOS V3 Application...")
        await runner.send("Page.navigate", {"url": "http://127.0.0.1:5173/"})
        await asyncio.sleep(4)

        # 1. Source & Facility Intelligence Workspace
        print("\n[View 1] Source & Facility Intelligence Workspace (4-Field & Spatial Tiers)...")
        await runner.evaluate("""
            const btns = Array.from(document.querySelectorAll('aside button'));
            const sfBtn = btns.find(b => b.textContent.includes('Source & Facility'));
            if (sfBtn) sfBtn.click();
        """)
        await asyncio.sleep(2.5)
        await runner.capture("01_phase2_source_facility_workspace.png")

        # 2. Facility Profile Drawer & CPCB Compliance Screening
        print("\n[View 2] Facility Profile Drawer & Regulatory Compliance Screening...")
        await runner.evaluate("""
            // Click the first persistent source card in the catalog
            const cards = Array.from(document.querySelectorAll('div.cursor-pointer'));
            const target = cards.find(c => c.textContent.includes('source_') || c.textContent.includes('Detections:'));
            if (target) target.click();
        """)
        await asyncio.sleep(2.5)
        await runner.capture("02_phase2_facility_profile_compliance.png")

        # 3. Thermal Analysis & FRP Engine Workspace
        print("\n[View 3] Thermal Analysis Workspace (FRP Stats & Diurnal Overpasses)...")
        await runner.evaluate("""
            const btns = Array.from(document.querySelectorAll('aside button'));
            const taBtn = btns.find(b => b.textContent.includes('Thermal Analysis'));
            if (taBtn) taBtn.click();
        """)
        await asyncio.sleep(2.5)
        await runner.capture("03_phase2_thermal_analysis_workspace.png")

        # 4. FRP Intensity Histogram & Temporal Trends
        print("\n[View 4] FRP Histogram Distribution & Temporal Trends...")
        await runner.evaluate("window.scrollBy(0, 380);")
        await asyncio.sleep(1)
        await runner.capture("04_phase2_frp_histogram_recurrence.png")

        # 5. Cluster Baseline Calculation (Leakage-Free Temporal Guard)
        print("\n[View 5] Cluster Baseline Calculator with Leakage Guard...")
        await runner.evaluate("""
            window.scrollTo(0, 0);
            const calcBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Calculate Baseline'));
            if (calcBtn) calcBtn.click();
        """)
        await asyncio.sleep(2)
        await runner.capture("05_phase2_cluster_baseline_leakage_protection.png")

        # 6. Risk Evaluation & Operational Priority Workspace
        print("\n[View 6] Risk & Prediction Workspace (Priority Queue & 4 Distinct Outputs)...")
        await runner.evaluate("""
            const btns = Array.from(document.querySelectorAll('aside button'));
            const rpBtn = btns.find(b => b.textContent.includes('Risk & Prediction'));
            if (rpBtn) rpBtn.click();
        """)
        await asyncio.sleep(2.5)
        await runner.capture("06_phase2_risk_prediction_workspace.png")

        # 7. Explainable Priority Component Breakdown
        print("\n[View 7] Explainable Priority Component Breakdown...")
        await runner.evaluate("""
            // Click the first priority queue item
            const items = Array.from(document.querySelectorAll('div.cursor-pointer'));
            const topItem = items.find(c => c.textContent.includes('CRITICAL') || c.textContent.includes('HIGH'));
            if (topItem) topItem.click();
        """)
        await asyncio.sleep(1.5)
        await runner.capture("07_phase2_explainable_priority_breakdown.png")

        # 8. Supervised Candidate Classifier Benchmarks
        print("\n[View 8] Supervised Candidate Classifier Benchmarks (Table & Calibration Disclaimer)...")
        await runner.evaluate("window.scrollBy(0, 520);")
        await asyncio.sleep(1)
        await runner.capture("08_phase2_supervised_model_benchmarks.png")

        # 9. Incident Investigations Workspace
        print("\n[View 9] AI-Assisted Incident Investigations Workspace (12 Dossiers Queue)...")
        await runner.evaluate("""
            window.scrollTo(0, 0);
            const btns = Array.from(document.querySelectorAll('aside button'));
            const invBtn = btns.find(b => b.textContent.includes('Incident Investigations'));
            if (invBtn) invBtn.click();
        """)
        await asyncio.sleep(2.5)
        await runner.capture("09_phase2_investigations_workspace.png")

        # 10. Investigation Review State Transition
        print("\n[View 10] Investigation Review State Transition...")
        await runner.evaluate("""
            const sel = document.querySelector('select');
            // Find status dropdown in the form
            const selects = Array.from(document.querySelectorAll('select'));
            const statusSel = selects.find(s => s.options && Array.from(s.options).some(o => o.value === 'Analyst reviewed'));
            if (statusSel) {
                statusSel.value = 'Analyst reviewed';
                statusSel.dispatchEvent(new Event('change', { bubbles: true }));
            }
            const txt = document.querySelector('textarea');
            if (txt) {
                txt.value = 'Verified high FRP exceedance against Bokaro industrial baseline. Dispatched for field verification.';
                txt.dispatchEvent(new Event('input', { bubbles: true }));
            }
            const commitBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Commit Status Transition'));
            if (commitBtn) commitBtn.click();
        """)
        await asyncio.sleep(2.5)
        await runner.capture("10_phase2_investigation_state_transition.png")

        # 11. AI Investigator Chat Drawer with Selected Dossier Context
        print("\n[View 11] Context-Aware AI Investigator Chat Drawer...")
        await runner.evaluate("""
            const aiBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Ask AI Investigator'));
            if (aiBtn) aiBtn.click();
        """)
        await asyncio.sleep(2.5)
        await runner.capture("11_phase2_ai_investigator_selected_context.png")

        print("\n" + "=" * 70)
        print("✓ ALL 11 PHASE 2 SCREENSHOTS CAPTURED SUCCESSFULLY!")
        print("=" * 70)

    finally:
        await runner.stop()


if __name__ == "__main__":
    asyncio.run(main())
