import sys
import os
import time

print("1. start")
t0 = time.time()
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

print("2. importing conftest")
import conftest
print(f"3. conftest done in {time.time()-t0:.2f}s, DATABASE_URL={os.environ.get('DATABASE_URL')}")

print("4. importing main")
t1 = time.time()
import main
print(f"5. main done in {time.time()-t1:.2f}s")

print("6. creating app")
t2 = time.time()
app = main.create_app()
print(f"7. app created in {time.time()-t2:.2f}s")
