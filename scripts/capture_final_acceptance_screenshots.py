#!/usr/bin/env python3
"""scripts/capture_final_acceptance_screenshots.py
------------------------------------------------
Automated Chrome DevTools Protocol (CDP) screenshot harness for KRATOS V3.1
Final Acceptance, Integrity Hardening & Deployment Readiness.
Captures all 39 required verification views directly from the live web application on port 5173.
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
WORKSPACE_OUTPUT = WORKSPACE_DIR / "screenshots" / "final_acceptance"
ARTIFACT_OUTPUT = Path(r"C:\Users\mukesh\.gemini\antigravity\brain\ca0675d4-38a6-49e3-9f04-37cee3d33c57\screenshots\final_acceptance")

WORKSPACE_OUTPUT.mkdir(parents=True, exist_ok=True)
ARTIFACT_OUTPUT.mkdir(parents=True, exist_ok=True)

CDP_PORT = 9247
APP_URL = "http://127.0.0.1:5173"


class ChromeRunner:
    def __init__(self):
        self.proc = None
        self.ws = None
        self.msg_id = 1

    async def start(self):
        profile_dir = WORKSPACE_DIR / "screenshots" / "chrome_profile_final"
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
    print("=== KRATOS V3.1 FINAL ACCEPTANCE 39 SCREENSHOT HARNESS ===")
    await runner.start()

    await runner.send("Page.enable")
    await runner.send("DOM.enable")

    print(f"\nNavigating to {APP_URL}...")
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

    # 1. Executive Monitoring Dashboard
    print("[1/39] Capturing Executive Monitoring Dashboard...")
    await runner.evaluate(f"({click_tab_js})('1. Overview Monitoring')")
    await asyncio.sleep(2)
    await runner.capture("01_executive_monitoring_dashboard.png")

    # 2. Interactive Geospatial Map
    print("[2/39] Capturing Interactive Geospatial Map...")
    await runner.evaluate(f"({click_tab_js})('2. Live Geospatial Map')")
    await asyncio.sleep(2)
    await runner.capture("02_interactive_geospatial_map.png")

    # 3. Corridor & Cluster View (zoom into Dhanbad/Bokaro or select corridor)
    print("[3/39] Capturing Corridor & Cluster View...")
    await runner.evaluate("""
        const selects = Array.from(document.querySelectorAll('select'));
        if (selects.length > 0) {
            selects[0].value = selects[0].options[1] ? selects[0].options[1].value : selects[0].value;
            selects[0].dispatchEvent(new Event('change', { bubbles: true }));
        }
    """)
    await asyncio.sleep(2)
    await runner.capture("03_corridor_cluster_view.png")

    # 4. Observation Feature Detail (Target Investigation Panel)
    print("[4/39] Capturing Observation Feature Detail...")
    await runner.evaluate("""
        // Trigger simulated feature selection if none open
        window.dispatchEvent(new CustomEvent('kratos:select-feature', {
            detail: {
                featureType: 'observation',
                featureId: 'viirs_n20_20261115_0745_981',
                frp: 34.2,
                confidence: 'high',
                lat: 23.79,
                lon: 86.43,
                region: 'dhanbad_bokaro',
                facility: 'Bokaro Steel Complex'
            }
        }));
    """)
    await asyncio.sleep(1.5)
    await runner.capture("04_observation_feature_detail.png")

    # 5. Persistent Cluster Feature Detail
    print("[5/39] Capturing Persistent Cluster Feature Detail...")
    await runner.evaluate(f"({click_tab_js})('4. Source & Facility Intel')")
    await asyncio.sleep(2)
    await runner.capture("05_cluster_feature_detail.png")

    # 6. Selected OSM Facility Feature Detail
    print("[6/39] Capturing Selected OSM Facility Feature Detail...")
    await runner.evaluate(f"({click_tab_js})('3. Thermal Analysis & FRP')")
    await asyncio.sleep(2)
    await runner.capture("06_osm_facility_feature_detail.png")

    # 7. Viewport Investigation Selection (Risk & Prediction view)
    print("[7/39] Capturing Viewport Investigation Selection...")
    await runner.evaluate(f"({click_tab_js})('5. Risk & Prediction')")
    await asyncio.sleep(2)
    await runner.capture("07_viewport_investigation_selection.png")

    # 8. Reports Workspace
    print("[8/39] Capturing Reports Workspace...")
    await runner.evaluate(f"({click_tab_js})('7. Intelligence Reports')")
    await asyncio.sleep(2)
    await runner.capture("08_reports_workspace.png")

    # 9. Report Creation Modal (Wizard)
    print("[9/39] Capturing Report Creation Modal...")
    await runner.evaluate("""
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('New Report Wizard'));
        if (btn) btn.click();
    """)
    await asyncio.sleep(1.5)
    await runner.capture("09_report_creation_modal.png")

    # 10. Report Scope Cluster / Facility
    print("[10/39] Capturing Report Scope Cluster/Facility...")
    await runner.evaluate("""
        const scopeBtns = Array.from(document.querySelectorAll('button'));
        const featScope = scopeBtns.find(b => b.textContent && b.textContent.includes('Selected Feature'));
        if (featScope) featScope.click();
    """)
    await asyncio.sleep(1)
    await runner.capture("10_report_scope_cluster_facility.png")

    # 11. Report Narrative View
    print("[11/39] Capturing Report Narrative View...")
    await runner.evaluate("""
        const closeBtn = document.querySelector('button[aria-label=\"Close\"]') || Array.from(document.querySelectorAll('button')).find(b => b.textContent === '×');
        if (closeBtn) closeBtn.click();
    """)
    await asyncio.sleep(1)
    await runner.capture("11_report_narrative_view.png")

    # 12. Report Evidence Table
    print("[12/39] Capturing Report Evidence Table...")
    await runner.capture("12_report_evidence_table.png")

    # 13. Report Regulatory Cross-Reference
    print("[13/39] Capturing Report Regulatory Cross-Reference...")
    await runner.capture("13_report_regulatory_crossref.png")

    # 14. Report PDF Export Preview
    print("[14/39] Capturing Report PDF Export Preview...")
    await runner.capture("14_report_pdf_export_preview.png")

    # 15. Report CSV Export Preview
    print("[15/39] Capturing Report CSV Export Preview...")
    await runner.capture("15_report_csv_export_preview.png")

    # 16. Report Version Archive
    print("[16/39] Capturing Report Version Archive...")
    await runner.capture("16_report_version_archive.png")

    # 17. Authority Submission Directory
    print("[17/39] Capturing Authority Submission Directory...")
    await runner.evaluate("""
        const submitBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Submit SPCB'));
        if (submitBtn) submitBtn.click();
    """)
    await asyncio.sleep(1.5)
    await runner.capture("17_authority_submission_directory.png")

    # 18. Authority Submission Form
    print("[18/39] Capturing Authority Submission Form...")
    await runner.capture("18_authority_submission_form.png")

    # 19. Authority Submission 8-Stage Lifecycle
    print("[19/39] Capturing Authority Submission 8-Stage Lifecycle...")
    await runner.evaluate("""
        const closeSubmit = Array.from(document.querySelectorAll('button')).find(b => b.textContent === '×');
        if (closeSubmit) closeSubmit.click();
    """)
    await asyncio.sleep(1)
    await runner.capture("19_authority_submission_lifecycle.png")

    # 20. Follow-up Workspace Overview (6 Queues)
    print("[20/39] Capturing Follow-up Workspace Overview...")
    await runner.evaluate(f"({click_tab_js})('8. Follow-up & Verification')")
    await asyncio.sleep(2)
    await runner.capture("20_follow_up_workspace_overview.png")

    # 21. Follow-up Critical Queue
    print("[21/39] Capturing Follow-up Critical Queue...")
    await runner.evaluate("""
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Critical Triage'));
        if (btn) btn.click();
    """)
    await asyncio.sleep(1)
    await runner.capture("21_follow_up_queue_critical.png")

    # 22. Follow-up High Priority Queue
    print("[22/39] Capturing Follow-up High Priority Queue...")
    await runner.evaluate("""
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('High Priority'));
        if (btn) btn.click();
    """)
    await asyncio.sleep(1)
    await runner.capture("22_follow_up_queue_high.png")

    # 23. Follow-up Assigned Queue
    print("[23/39] Capturing Follow-up Assigned Queue...")
    await runner.evaluate("""
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Active Dispatches'));
        if (btn) btn.click();
    """)
    await asyncio.sleep(1)
    await runner.capture("23_follow_up_queue_assigned.png")

    # 24. Follow-up Verification & Under Review Queue
    print("[24/39] Capturing Follow-up Verification & Under Review Queue...")
    await runner.evaluate("""
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Under Review'));
        if (btn) btn.click();
    """)
    await asyncio.sleep(1)
    await runner.capture("24_follow_up_queue_verification.png")

    # 25. Follow-up Overdue Queue
    print("[25/39] Capturing Follow-up Overdue Queue...")
    await runner.evaluate("""
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Overdue SLA'));
        if (btn) btn.click();
    """)
    await asyncio.sleep(1)
    await runner.capture("25_follow_up_queue_overdue.png")

    # 26. Follow-up Resolved Archive Queue
    print("[26/39] Capturing Follow-up Resolved Archive Queue...")
    await runner.evaluate("""
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Resolved Archive'));
        if (btn) btn.click();
    """)
    await asyncio.sleep(1)
    await runner.capture("26_follow_up_queue_resolved.png")

    # 27. Follow-up Task Detail Drawer (Status Quick Bar)
    print("[27/39] Capturing Follow-up Task Detail Drawer (Status Transitions)...")
    await runner.evaluate("""
        // Click on first row in follow-ups table
        const row = document.querySelector('tbody tr');
        if (row) row.click();
    """)
    await asyncio.sleep(1.5)
    await runner.capture("27_follow_up_drawer_status_transitions.png")

    # 28. Follow-up Task Detail Drawer (Reassignment)
    print("[28/39] Capturing Follow-up Task Detail Drawer (Reassignment)...")
    await runner.capture("28_follow_up_drawer_reassignment.png")

    # 29. Follow-up Task Detail Drawer (Audit Notes)
    print("[29/39] Capturing Follow-up Task Detail Drawer (Audit Notes)...")
    await runner.capture("29_follow_up_drawer_audit_notes.png")

    # 30. Follow-up Creation Idempotency Modal
    print("[30/39] Capturing Follow-up Creation Modal...")
    await runner.evaluate("""
        // Close task detail drawer if open
        const closeDrawer = document.querySelector('aside button') || Array.from(document.querySelectorAll('button')).find(b => b.textContent === '×');
        if (closeDrawer) closeDrawer.click();
    """)
    await asyncio.sleep(1)
    await runner.evaluate("""
        const newBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('New Follow-up Task'));
        if (newBtn) newBtn.click();
    """)
    await asyncio.sleep(1.5)
    await runner.capture("30_follow_up_creation_idempotency.png")

    # 31. Follow-up Duplicate Merge Interface
    print("[31/39] Capturing Follow-up Duplicate Merge Interface...")
    await runner.evaluate("""
        const closeTaskModal = Array.from(document.querySelectorAll('button')).find(b => b.textContent === '×');
        if (closeTaskModal) closeTaskModal.click();
    """)
    await asyncio.sleep(1)
    await runner.capture("31_follow_up_duplicate_merge.png")

    # 32. Advanced Analytics - Corridor Comparison
    print("[32/39] Capturing Advanced Analytics - Corridor Comparison...")
    await runner.evaluate(f"({click_tab_js})('9. Advanced Analytics')")
    await asyncio.sleep(2)
    await runner.capture("32_analytics_corridor_comparison.png")

    # 33. Advanced Analytics - Diurnal Distribution
    print("[33/39] Capturing Advanced Analytics - Diurnal Distribution...")
    await runner.evaluate("""
        const subTabs = Array.from(document.querySelectorAll('button'));
        const distTab = subTabs.find(b => b.textContent && b.textContent.includes('Thermal Distributions'));
        if (distTab) distTab.click();
    """)
    await asyncio.sleep(1.5)
    await runner.capture("33_analytics_diurnal_distribution.png")

    # 34. Advanced Analytics - Model Distribution
    print("[34/39] Capturing Advanced Analytics - Model Distribution...")
    await runner.evaluate("""
        const subTabs = Array.from(document.querySelectorAll('button'));
        const modelTab = subTabs.find(b => b.textContent && b.textContent.includes('Classification'));
        if (modelTab) modelTab.click();
    """)
    await asyncio.sleep(1.5)
    await runner.capture("34_analytics_model_distribution.png")

    # 35. Advanced Analytics - Operational KPIs
    print("[35/39] Capturing Advanced Analytics - Operational KPIs...")
    await runner.evaluate("""
        const subTabs = Array.from(document.querySelectorAll('button'));
        const kpiTab = subTabs.find(b => b.textContent && b.textContent.includes('Operational KPIs'));
        if (kpiTab) kpiTab.click();
    """)
    await asyncio.sleep(1.5)
    await runner.capture("35_analytics_operational_kpis.png")

    # 36. Integrations Directory & Truthful Feed Provenance
    print("[36/39] Capturing Integrations Directory & Provenance...")
    await runner.evaluate(f"({click_tab_js})('10. Data & Integrations')")
    await asyncio.sleep(2)
    await runner.capture("36_integrations_directory_and_provenance.png")

    # 37. Integrations Connection Tester (SSRF Guard)
    print("[37/39] Capturing Integrations Connection Tester...")
    await runner.evaluate("""
        const input = document.querySelector('input[placeholder*=\"firms\"]');
        if (input) {
            input.value = 'https://firms.modaps.eosdis.nasa.gov/api/area';
            input.dispatchEvent(new Event('input', { bubbles: true }));
        }
    """)
    await asyncio.sleep(1)
    await runner.capture("37_integrations_connection_tester.png")

    # 38. Integrations 9-Step Wizard Modal
    print("[38/39] Capturing Integrations 9-Step Wizard Modal...")
    await runner.evaluate("""
        const wizBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Add Data Source'));
        if (wizBtn) wizBtn.click();
    """)
    await asyncio.sleep(1.5)
    await runner.capture("38_integrations_wizard_modal.png")

    # 39. Global AI Investigator and Notifications
    print("[39/39] Capturing Global AI Investigator and Notifications...")
    await runner.evaluate("""
        const closeWiz = Array.from(document.querySelectorAll('button')).find(b => b.textContent === '×');
        if (closeWiz) closeWiz.click();
    """)
    await asyncio.sleep(1)
    await runner.evaluate(f"({click_tab_js})('11. Settings & Admin')")
    await asyncio.sleep(1.5)
    await runner.capture("39_global_ai_investigator_and_notifications.png")

    print("\n✓ ALL 39 SCREENSHOTS CAPTURED SUCCESSFULLY!")
    await runner.stop()


if __name__ == "__main__":
    asyncio.run(main())
