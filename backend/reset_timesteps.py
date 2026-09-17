"""
reset_timesteps.py
------------------
Resets all 'failed' STATUS.json files across event timesteps back to 'pending'
so the pipeline will retry them on next startup.

Run from the backend directory:
    python reset_timesteps.py
"""
import json
from pathlib import Path


def reset_failed_timesteps() -> int:
    data_dir = Path(__file__).resolve().parent.parent / "data" / "events"
    if not data_dir.exists():
        print("No events directory found.")
        return 0

    reset_count = 0
    for status_path in data_dir.rglob("STATUS.json"):
        try:
            content = json.loads(status_path.read_text(encoding="utf-8"))
            if content.get("status") == "failed":
                content["status"] = "pending"
                status_path.write_text(json.dumps(content, indent=2), encoding="utf-8")
                reset_count += 1
        except Exception as e:
            print(f"Error checking {status_path}: {e}")

    print(f"Reset {reset_count} failed status file(s) back to pending.")
    return reset_count


if __name__ == "__main__":
    reset_failed_timesteps()
