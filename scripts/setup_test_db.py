import os
import sys
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env.test")
load_dotenv(REPO_ROOT / ".env")

# Add backend to path
sys.path.insert(0, str(REPO_ROOT / "backend"))

test_db_url = os.getenv("TEST_DATABASE_URL")
if not test_db_url:
    raise RuntimeError("TEST_DATABASE_URL must be set to run setup_test_db.py")

os.environ["DATABASE_URL"] = test_db_url

from main import create_app
from db.connection import db
import db.models  # ensure all models registered

app = create_app()
with app.app_context():
    print("Creating all tables in wildfire_test_db...")
    db.create_all()
    print("All tables created successfully in wildfire_test_db!")
