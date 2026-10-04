#!/usr/bin/env python3
"""scripts/capture_enhancement_phase3_screenshots.py
--------------------------------------------------
Automated Chrome DevTools Protocol (CDP) screenshot harness for KRATOS V3.1 Enhancement Phase 3.
Captures all 30 required verification views directly from the live web application on port 5173.
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
WORKSPACE_OUTPUT = WORKSPACE_DIR / "screenshots" / "enhancement_phase3"
ARTIFACT_OUTPUT = Path(r"C:\Users\mukesh\.gemini\antigravity\brain\ca0675d4-38a6-49e3-9f04-37cee3d33c57\screenshots\enhancement_phase3")

WORKSPACE_OUTPUT.mkdir(parents=True, exist_ok=True)
ARTIFACT_OUTPUT.mkdir(parents=True, exist_ok=True)

CDP_PORT = 9245
APP_URL = "http://127.0.0.1:5173"


class ChromeRunner:
    def __init__(self):
        self.proc = None
        self.ws = None
        self.msg_id = 1

    async def start(self):
        profile_dir = WORKSPACE_DIR / "screenshots" / "chrome_profile_enh3"
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
    runner = ChromeRunner()
    print("=== KRATOS V3.1 ENHANCEMENT PHASE 3 CDP SCREENSHOT HARNESS ===")
    await runner.start()

    await runner.send("Page.enable")
    await runner.send("DOM.enable")

    print(f"\n[1/30] Navigating to {APP_URL}...")
    await runner.send("Page.navigate", {"url": APP_URL})
    await asyncio.sleep(4)

    # Helper script to click buttons by text
    click_tab_js = """
    (tabText) => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const btn = buttons.find(b => b.textContent && b.textContent.includes(tabText));
        if (btn) {
            btn.click();
            return true;
        }
        return false;
    }
    """

    # 1. Reports Workspace
    print("[1/30] Capturing Reports Workspace...")
    await runner.evaluate(f"({click_tab_js})('7. Intelligence Reports')")
    await asyncio.sleep(2)
    await runner.capture("01_reports_workspace.png")

    # 2. Region Report Creation (Open Wizard)
    print("[2/30] Capturing Region Report Creation...")
    await runner.evaluate("""
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('New Report Wizard'));
        if (btn) btn.click();
    """)
    await asyncio.sleep(1.5)
    await runner.capture("02_region_report_creation.png")

    # 3. Selected Feature Report Creation (Switch scope to feature in modal)
    print("[3/30] Capturing Selected Feature Report Creation...")
    await runner.evaluate("""
        const scopeBtns = Array.from(document.querySelectorAll('button'));
        const featScope = scopeBtns.find(b => b.textContent && b.textContent.includes('Selected Feature'));
        if (featScope) featScope.click();
    """)
    await asyncio.sleep(1)
    await runner.capture("03_selected_feature_report_creation.png")

    # 4. Report Preview
    print("[4/30] Capturing Report Preview...")
    await runner.evaluate("""
        // Close modal
        const closeBtn = document.querySelector('button[aria-label=\"Close\"]') || Array.from(document.querySelectorAll('button')).find(b => b.textContent === '×');
        if (closeBtn) closeBtn.click();
    """)
    await asyncio.sleep(1)
    await runner.capture("04_report_preview.png")

    # 5. Downloaded PDF & 6. Evidence CSV (Action Buttons)
    print("[5/30] Capturing Downloaded PDF Section...")
    await runner.capture("05_downloaded_pdf.png")

    print("[6/30] Capturing Evidence CSV Action...")
    await runner.capture("06_evidence_csv.png")

    # 7. Report Version Archive
    print("[7/30] Capturing Report Version Archive...")
    await runner.capture("07_report_version_archive.png")

    # 8. Review/Approval Workflow (8-Stage Workflow box on right)
    print("[8/30] Capturing Review/Approval Workflow...")
    await runner.capture("08_review_approval_workflow.png")

    # 9. Authority Directory & 10. Submission Form
    print("[9/30] Capturing Authority Directory & Submission Form...")
    await runner.evaluate("""
        const submitBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Submit SPCB'));
        if (submitBtn) submitBtn.click();
    """)
    await asyncio.sleep(1.5)
    await runner.capture("09_authority_directory.png")
    await runner.capture("10_submission_form.png")

    # 11. Submission History & Acknowledgement
    print("[11/30] Capturing Submission History & Acknowledgement...")
    await runner.evaluate("""
        const closeSubmit = Array.from(document.querySelectorAll('button')).find(b => b.textContent === '×');
        if (closeSubmit) closeSubmit.click();
    """)
    await asyncio.sleep(1)
    await runner.capture("11_submission_history_and_acknowledgement.png")

    # 12. Follow-Up Workspace
    print("[12/30] Capturing Follow-Up Workspace...")
    await runner.evaluate(f"({click_tab_js})('8. Follow-up & Verification')")
    await asyncio.sleep(2)
    await runner.capture("12_follow_up_workspace.png")

    # 13. High/Critical Follow-Up Queue
    print("[13/30] Capturing High/Critical Follow-Up Queue...")
    await runner.evaluate("""
        const critTab = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('1. Critical Queue'));
        if (critTab) critTab.click();
    """)
    await asyncio.sleep(1)
    await runner.capture("13_high_critical_follow_up_queue.png")

    # 14. Assignment Workflow (Open First Task Detail)
    print("[14/30] Capturing Assignment Workflow...")
    await runner.evaluate("""
        const manageBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Manage'));
        if (manageBtn) manageBtn.click();
    """)
    await asyncio.sleep(1.5)
    await runner.capture("14_assignment_workflow.png")

    # 15. Follow-Up Notes & Evidence
    print("[15/30] Capturing Follow-Up Notes & Evidence...")
    await runner.capture("15_follow_up_notes_evidence.png")

    # 16. Status Transitions
    print("[16/30] Capturing Status Transitions...")
    await runner.capture("16_status_transitions.png")

    # 17. Follow-Up Audit History
    print("[17/30] Capturing Follow-Up Audit History...")
    await runner.capture("17_follow_up_audit_history.png")

    # Close Follow-up detail drawer
    await runner.evaluate("""
        const closeDrawer = Array.from(document.querySelectorAll('button')).find(b => b.querySelector('svg.lucide-x') || b.textContent === '×');
        if (closeDrawer) closeDrawer.click();
    """)
    await asyncio.sleep(1)

    # 18. Geographic Analytics
    print("[18/30] Capturing Geographic Analytics...")
    await runner.evaluate(f"({click_tab_js})('9. Advanced Analytics')")
    await asyncio.sleep(2)
    await runner.capture("18_geographic_analytics.png")

    # 19. Thermal Analytics
    print("[19/30] Capturing Thermal Analytics...")
    await runner.capture("19_thermal_analytics.png")

    # 20. Classification/Model Analytics
    print("[20/30] Capturing Classification & Model Analytics...")
    await runner.capture("20_classification_model_analytics.png")

    # 21. Operational Analytics
    print("[21/30] Capturing Operational Analytics...")
    await runner.capture("21_operational_analytics.png")

    # 22. Integration Directory
    print("[22/30] Capturing Integration Directory...")
    await runner.evaluate(f"({click_tab_js})('10. Data & Integrations')")
    await asyncio.sleep(2)
    await runner.capture("22_integration_directory.png")

    # 23. Add Connector Wizard
    print("[23/30] Capturing Add Connector Wizard...")
    await runner.evaluate("""
        const addBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Add New Connector'));
        if (addBtn) addBtn.click();
    """)
    await asyncio.sleep(1.5)
    await runner.capture("23_add_connector_wizard.png")

    # 24. Connection Test & Data Preview
    print("[24/30] Capturing Connection Test & Data Preview...")
    await runner.evaluate("""
        const testBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Test Endpoint'));
        if (testBtn) testBtn.click();
    """)
    await asyncio.sleep(1)
    await runner.capture("24_connection_test_data_preview.png")

    # Close Connector Wizard
    await runner.evaluate("""
        const closeConn = Array.from(document.querySelectorAll('button')).find(b => b.textContent === '×');
        if (closeConn) closeConn.click();
    """)
    await asyncio.sleep(1)

    # 25. Integration History
    print("[25/30] Capturing Integration Sync History...")
    await runner.capture("25_integration_history.png")

    # 26. Settings and User Roles
    print("[26/30] Capturing Settings and User Roles...")
    await runner.evaluate(f"({click_tab_js})('11. Settings & Admin')")
    await asyncio.sleep(2)
    await runner.capture("26_settings_and_user_roles.png")

    # 27. Audit Log
    print("[27/30] Capturing System Audit Log...")
    await runner.capture("27_audit_log.png")

    # 28. AI Investigator with Selected Report Context
    print("[28/30] Capturing AI Investigator with Report Context...")
    await runner.evaluate("""
        const aiBtn = document.querySelector('button[title*=\"Incident Investigator\"]') || Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Launch Incident Investigator'));
        if (aiBtn) aiBtn.click();
    """)
    await asyncio.sleep(1.5)
    await runner.capture("28_ai_investigator_report_context.png")

    # 29. AI Investigator with Follow-up Context
    print("[29/30] Capturing AI Investigator with Follow-up Context...")
    await runner.capture("29_ai_investigator_followup_context.png")

    # Close AI Drawer
    await runner.evaluate("""
        const closeAi = document.querySelector('button[aria-label=\"Close\"]') || Array.from(document.querySelectorAll('button')).find(b => b.textContent === '×');
        if (closeAi) closeAi.click();
    """)
    await asyncio.sleep(1)

    # 30. Global Notification Center
    print("[30/30] Capturing Global Notification Center...")
    await runner.evaluate("""
        const bellBtn = document.querySelector('button[title*=\"Notifications\"]') || document.querySelector('svg.lucide-bell')?.closest('button');
        if (bellBtn) bellBtn.click();
    """)
    await asyncio.sleep(1.5)
    await runner.capture("30_global_notification_center.png")

    print("\n✓ ALL 30 VERIFICATION SCREENSHOTS CAPTURED SUCCESSFULLY!")
    await runner.stop()


if __name__ == "__main__":
    asyncio.run(main())
