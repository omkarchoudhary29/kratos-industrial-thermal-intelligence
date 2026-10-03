import unittest
import json
import uuid
from main import create_app
from db.connection import db
from db.models import InvestigationReport, FollowUpTask, FollowUpNote

class ReportsAndFollowupsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    def test_01_report_generation_and_export(self):
        # 1. Generate Region Report
        payload = {
            "scope": "region",
            "region_id": "singrauli_sonbhadra",
            "region_name": "Singrauli-Sonbhadra Energy Corridor"
        }
        res = self.client.post(
            "/api/v1/reports/generate",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        report_id = data["id"]
        report_key = data["report_key"]
        self.assertTrue(report_key.startswith("RPT-"))
        self.assertIn("summary", data)
        self.assertIn("evidence", data)
        self.assertEqual(data["scope"], "region")

        # 2. List Reports
        list_res = self.client.get("/api/v1/reports")
        self.assertEqual(list_res.status_code, 200)
        list_data = list_res.get_json()
        self.assertGreaterEqual(list_data["total"], 1)

        # 3. Download PDF
        pdf_res = self.client.get(f"/api/v1/reports/{report_id}/pdf")
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.content_type, "application/pdf")
        self.assertTrue(pdf_res.data.startswith(b"%PDF"))

        # 4. Download Evidence CSV
        csv_res = self.client.get(f"/api/v1/reports/{report_id}/csv")
        self.assertEqual(csv_res.status_code, 200)
        self.assertIn(b"report_id,scope,region_name", csv_res.data)

    def test_02_followup_lifecycle(self):
        # 1. Create Follow-up Task
        payload = {
            "title": "Verify elevated FRP flare stack in Bokaro",
            "feature_type": "cluster",
            "feature_id": f"dhanbad_bokaro_source_10_{uuid.uuid4().hex[:6]}",
            "region_name": "dhanbad_bokaro",
            "priority": "HIGH",
            "status": "OPEN",
            "description": "Routine satellite surveillance flagged 10.8x baseline ratio.",
            "force": True
        }
        res = self.client.post(
            "/api/v1/followups",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        task = res.get_json()
        task_id = task["id"]
        self.assertEqual(task["status"], "OPEN")
        self.assertEqual(task["priority"], "HIGH")

        # 2. Update Status
        patch_res = self.client.patch(
            f"/api/v1/followups/{task_id}",
            data=json.dumps({"status": "IN_PROGRESS", "note": "Assigned to ground drone patrol"}),
            content_type="application/json"
        )
        self.assertEqual(patch_res.status_code, 200)
        updated = patch_res.get_json()
        self.assertEqual(updated["status"], "IN_PROGRESS")

        # 3. Add Note
        note_res = self.client.post(
            f"/api/v1/followups/{task_id}/notes",
            data=json.dumps({
                "note_text": "Field patrol confirmed controlled coke oven battery quenching flare.",
                "status_change": "RESOLVED"
            }),
            content_type="application/json"
        )
        self.assertEqual(note_res.status_code, 201)
        note_data = note_res.get_json()
        self.assertEqual(note_data["status_change"], "RESOLVED")

        # 4. Verify Task is now RESOLVED with notes
        get_res = self.client.get(f"/api/v1/followups/{task_id}")
        self.assertEqual(get_res.status_code, 200)
        final_task = get_res.get_json()
        self.assertEqual(final_task["status"], "RESOLVED")
        self.assertGreaterEqual(len(final_task["notes"]), 2)

if __name__ == "__main__":
    unittest.main()
