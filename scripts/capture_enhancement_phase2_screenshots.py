#!/usr/bin/env python3
"""scripts/capture_enhancement_phase2_screenshots.py
--------------------------------------------------
Automated Chrome DevTools Protocol (CDP) screenshot harness for KRATOS V3.1 Enhancement Phase 2.
Captures all 13 required verification views directly from the live web application on port 5173.
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
WORKSPACE_DIR = Path(r"D:\mukesh\Documents\Gen ai\industrial-thermal-intelligence")
WORKSPACE_OUTPUT = WORKSPACE_DIR / "screenshots" / "enhancement_phase2"
ARTIFACT_OUTPUT = Path(r"C:\Users\mukesh\.gemini\antigravity\brain\ca0675d4-38a6-49e3-9f04-37cee3d33c57\screenshots\enhancement_phase2")

WORKSPACE_OUTPUT.mkdir(parents=True, exist_ok=True)
ARTIFACT_OUTPUT.mkdir(parents=True, exist_ok=True)

CDP_PORT = 9244
APP_URL = "http://127.0.0.1:5173"


class ChromeRunner:
    def __init__(self):
        self.proc = None
        self.ws = None
        self.msg_id = 1

    async def start(self):
        profile_dir = WORKSPACE_DIR / "screenshots" / "chrome_profile_enh2"
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


async def main():
    print("=" * 80)
    print(" KRATOS V3.1 ENHANCEMENT PHASE 2 — AUTOMATED SCREENSHOT CAPTURE")
    print(f" Target URL: {APP_URL}")
    print(f" Workspace Output: {WORKSPACE_OUTPUT}")
    print(f" Artifact Output:  {ARTIFACT_OUTPUT}")
    print("=" * 80)

    runner = ChromeRunner()
    await runner.start()

    try:
        await runner.send("Page.enable")
        await runner.send("Runtime.enable")

        print("\n[1/13] Navigating to KRATOS application...")
        await runner.send("Page.navigate", {"url": APP_URL})
        await asyncio.sleep(5)

        # Dismiss any welcome/auth modals
        await runner.evaluate("""
            const btns = Array.from(document.querySelectorAll('button'));
            const closeBtn = btns.find(b => b.innerText.includes('Explore Dashboard') || b.innerText.includes('Dismiss') || b.innerText.includes('Continue'));
            if (closeBtn) closeBtn.click();
        """)
        await asyncio.sleep(2)

        # ── 1. 01_evidence_bundle_inspection.png ──────────────────────────────
        print("[2/13] Capturing 01_evidence_bundle_inspection.png (Target Investigation Panel)...")
        # Click first persistent source or detection row to open target panel
        await runner.evaluate("""
            const rows = Array.from(document.querySelectorAll('tr, div[class*="cursor-pointer"]'));
            const row = rows.find(r => r.innerText.includes('dhanbad_bokaro') || r.innerText.includes('source_10') || r.innerText.includes('MW'));
            if (row) row.click();
        """)
        await asyncio.sleep(3)
        await runner.capture("01_evidence_bundle_inspection.png")

        # ── 2. 02_multilevel_historical_baselines.png ─────────────────────────
        print("[3/13] Capturing 02_multilevel_historical_baselines.png (Tab 3: Thermal Analysis)...")
        await runner.evaluate("""
            const tabs = Array.from(document.querySelectorAll('button'));
            const tab = tabs.find(b => b.innerText.includes('Thermal Analysis'));
            if (tab) tab.click();
        """)
        await asyncio.sleep(3)
        # Click Calculate Baseline
        await runner.evaluate("""
            const btns = Array.from(document.querySelectorAll('button'));
            const btn = btns.find(b => b.innerText.includes('Calculate Baseline'));
            if (btn) btn.click();
        """)
        await asyncio.sleep(3)
        await runner.capture("02_multilevel_historical_baselines.png")

        # ── 3. 03_baseline_maturity_tiers.png ─────────────────────────────────
        print("[4/13] Capturing 03_baseline_maturity_tiers.png (Maturity Tiers & Data Sufficiency)...")
        # Scroll to baseline section
        await runner.evaluate("""
            window.scrollBy({ top: 350, behavior: 'smooth' });
        """)
        await asyncio.sleep(2)
        await runner.capture("03_baseline_maturity_tiers.png")

        # ── 4. 04_multimodel_anomaly_detection.png ────────────────────────────
        print("[5/13] Capturing 04_multimodel_anomaly_detection.png (Multi-Model Anomaly Consensus)...")
        # Switch back to Tab 1 to show target panel multi-model consensus
        await runner.evaluate("""
            const tabs = Array.from(document.querySelectorAll('button'));
            const tab = tabs.find(b => b.innerText.includes('Monitoring Dashboard') || b.innerText.includes('Overview'));
            if (tab) tab.click();
        """)
        await asyncio.sleep(3)
        await runner.evaluate("""
            const rows = Array.from(document.querySelectorAll('tr, div[class*="cursor-pointer"]'));
            const row = rows.find(r => r.innerText.includes('dhanbad_bokaro') || r.innerText.includes('source_10'));
            if (row) row.click();
        """)
        await asyncio.sleep(2)
        await runner.capture("04_multimodel_anomaly_detection.png")

        # ── 5. 05_iforest_statistical_cusum_agreement.png ─────────────────────
        print("[6/13] Capturing 05_iforest_statistical_cusum_agreement.png (Tab 5: Risk & Prediction)...")
        await runner.evaluate("""
            const tabs = Array.from(document.querySelectorAll('button'));
            const tab = tabs.find(b => b.innerText.includes('Risk & Prediction'));
            if (tab) tab.click();
        """)
        await asyncio.sleep(3)
        # Select first queue item
        await runner.evaluate("""
            const cards = Array.from(document.querySelectorAll('div[class*="cursor-pointer"]'));
            if (cards.length > 0) cards[0].click();
        """)
        await asyncio.sleep(2)
        await runner.capture("05_iforest_statistical_cusum_agreement.png")

        # ── 6. 06_industrial_source_taxonomy.png ──────────────────────────────
        print("[7/13] Capturing 06_industrial_source_taxonomy.png (Tab 4: Source & Facility)...")
        await runner.evaluate("""
            const tabs = Array.from(document.querySelectorAll('button'));
            const tab = tabs.find(b => b.innerText.includes('Source & Facility'));
            if (tab) tab.click();
        """)
        await asyncio.sleep(3)
        await runner.capture("06_industrial_source_taxonomy.png")

        # ── 7. 07_engineering_vs_satellite_temperature.png ────────────────────
        print("[8/13] Capturing 07_engineering_vs_satellite_temperature.png (Scientific Distinction)...")
        # Click on first item in source catalog to open drawer
        await runner.evaluate("""
            const items = Array.from(document.querySelectorAll('div[class*="cursor-pointer"]'));
            if (items.length > 0) items[0].click();
        """)
        await asyncio.sleep(2)
        # Scroll right drawer down to show scientific distinction card
        await runner.evaluate("""
            const drawer = document.querySelector('div[class*="sticky"]');
            if (drawer) drawer.scrollIntoView({ behavior: 'smooth' });
        """)
        await asyncio.sleep(2)
        await runner.capture("07_engineering_vs_satellite_temperature.png")

        # ── 8. 08_hierarchical_source_classification.png ──────────────────────
        print("[9/13] Capturing 08_hierarchical_source_classification.png (Hierarchical Classification)...")
        await runner.capture("08_hierarchical_source_classification.png")

        # ── 9. 09_honest_incident_risk_ground_truth.png ───────────────────────
        print("[10/13] Capturing 09_honest_incident_risk_ground_truth.png (Honest Ground-Truth Policy)...")
        await runner.evaluate("""
            const tabs = Array.from(document.querySelectorAll('button'));
            const tab = tabs.find(b => b.innerText.includes('Risk & Prediction'));
            if (tab) tab.click();
        """)
        await asyncio.sleep(3)
        await runner.capture("09_honest_incident_risk_ground_truth.png")

        # ── 10. 10_operational_priority_score_breakdown.png ───────────────────
        print("[11/13] Capturing 10_operational_priority_score_breakdown.png (Operational Priority Breakdown)...")
        await runner.evaluate("""
            window.scrollBy({ top: 200, behavior: 'smooth' });
        """)
        await asyncio.sleep(2)
        await runner.capture("10_operational_priority_score_breakdown.png")

        # ── 11. 11_ai_investigator_evidence_grounded.png ──────────────────────
        print("[12/13] Capturing 11_ai_investigator_evidence_grounded.png (AI Investigator)...")
        await runner.evaluate("""
            const btns = Array.from(document.querySelectorAll('button'));
            const aiBtn = btns.find(b => b.innerText.includes('AI Investigator') || b.title?.includes('AI Investigator') || b.querySelector('svg'));
            if (aiBtn) aiBtn.click();
        """)
        await asyncio.sleep(2)
        # Send a prompt to AI Investigator
        await runner.evaluate("""
            const textarea = document.querySelector('textarea, input[placeholder*="Ask"]');
            if (textarea) {
                textarea.value = 'What is the thermal baseline and operational priority for this industrial facility?';
                textarea.dispatchEvent(new Event('input', { bubbles: true }));
                const sendBtn = textarea.parentElement.querySelector('button');
                if (sendBtn) sendBtn.click();
            }
        """)
        await asyncio.sleep(5)
        await runner.capture("11_ai_investigator_evidence_grounded.png")

        # Close AI drawer
        await runner.evaluate("""
            const closeBtns = Array.from(document.querySelectorAll('button'));
            const close = closeBtns.find(b => b.title?.includes('Close') || b.ariaLabel?.includes('Close'));
            if (close) close.click();
        """)
        await asyncio.sleep(1)

        # ── 12. 12_investigation_evidence_dossier.png ─────────────────────────
        print("[13/13] Capturing 12_investigation_evidence_dossier.png (Tab 6: Investigations)...")
        await runner.evaluate("""
            const tabs = Array.from(document.querySelectorAll('button'));
            const tab = tabs.find(b => b.innerText.includes('Investigations'));
            if (tab) tab.click();
        """)
        await asyncio.sleep(3)
        # Select first investigation
        await runner.evaluate("""
            const invs = Array.from(document.querySelectorAll('div[class*="cursor-pointer"]'));
            if (invs.length > 0) invs[0].click();
        """)
        await asyncio.sleep(2)
        await runner.capture("12_investigation_evidence_dossier.png")

        # ── 13. 13_pan_india_intelligence_overview.png ────────────────────────
        print("[14/13] Capturing 13_pan_india_intelligence_overview.png (Pan-India Overview)...")
        await runner.evaluate("""
            const tabs = Array.from(document.querySelectorAll('button'));
            const tab = tabs.find(b => b.innerText.includes('Monitoring Dashboard') || b.innerText.includes('Overview'));
            if (tab) tab.click();
        """)
        await asyncio.sleep(2)
        # Zoom out / pan map view
        await runner.evaluate("""
            window.scrollTo({ top: 0, behavior: 'smooth' });
        """)
        await asyncio.sleep(3)
        await runner.capture("13_pan_india_intelligence_overview.png")

        print("\n" + "=" * 80)
        print(" ALL 13 ENHANCEMENT PHASE 2 SCREENSHOTS CAPTURED SUCCESSFULLY!")
        print("=" * 80)

    finally:
        await runner.stop()


if __name__ == "__main__":
    asyncio.run(main())
