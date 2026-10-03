import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
import config
from db.connection import get_db_uri
from db.models import InvestigationReport, FollowUpTask, AuthoritySubmission
from services.report_intelligence import generate_report_pdf, generate_report_evidence_csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def test_exports():
    engine = create_engine(get_db_uri())
    Session = sessionmaker(bind=engine)
    session = Session()

    report = session.query(InvestigationReport).order_by(InvestigationReport.id.desc()).first()
    if report:
        pdf_bytes = generate_report_pdf(report)
        print(f"Report {report.id} ({report.report_key}) PDF generated: {len(pdf_bytes)} bytes")
        csv_str = generate_report_evidence_csv(report)
        print(f"Report {report.id} CSV generated: {len(csv_str)} characters")
        print("CSV preview:")
        print(csv_str[:300])

        # Write to disk to inspect
        pdf_path = Path(__file__).resolve().parent.parent / f"report_{report.id}.pdf"
        pdf_path.write_bytes(pdf_bytes)
        print(f"Saved PDF to {pdf_path}")
    else:
        print("No reports found.")

if __name__ == "__main__":
    test_exports()
