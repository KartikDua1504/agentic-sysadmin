"""
Setup script for the "pls_adopt_me" task.

This script simulates a stale file lock caused by an orphaned background process.

Scenario:
- A database file (/opt/app/production.db) is locked by a rogue process
- The locking process detaches (forks) and continues running in the background
- A startup script enforces a single-instance lock using `flock`

Failure:
- The application cannot start because the file is already locked
- A PID file exists but does not correspond to a properly managed process

Key mechanics:
- fcntl.flock creates an exclusive lock on the database file
- The rogue process forks and detaches → becomes orphaned
- The parent exits, leaving the child holding the lock indefinitely

Expected fix:
- Identify and terminate the process holding the file lock (e.g., via lsof/fuser)
- Restart the application successfully

Important:
- Simulates real-world stale lock / orphaned process issues
- Requires understanding of file locks and process lifecycle
"""

import os
import subprocess
from pathlib import Path

def write_text(path: str, content: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

def setup():
    print("Setting up pls_adopt_me directly on /...")

    os.makedirs("/opt/app", exist_ok=True)
    Path("/opt/app/production.db").touch()

    # Rogue worker: acquires lock, forks, and leaves orphan holding it indefinitely
    rogue_worker_py = """\
import os, time, fcntl
db = open("/opt/app/production.db", "w")
fcntl.flock(db, fcntl.LOCK_EX)
parent_pid = os.getpid()
with open("/opt/app/app.pid", "w") as pidfile:
    pidfile.write(str(parent_pid))
if os.fork() > 0:
    os._exit(0)
else:
    while True: time.sleep(1)
"""
    write_text("/opt/app/rogue_worker.py", rogue_worker_py)
    
    # 2. Startup script with single-instance guard.
    start_app_sh = """#!/bin/bash
exec 9>/opt/app/production.db
if ! flock -n 9; then
  echo "FATAL: production.db is locked by another process! Check /opt/app/app.pid"
  exit 1
fi
echo "SUCCESS: Database lock acquired. App Booted!"
"""
    write_text("/usr/local/bin/start_app.sh", start_app_sh)
    os.chmod("/usr/local/bin/start_app.sh", 0o755)

    # 3. Execute the rogue worker so it locks the file and orphans itself!
    subprocess.run(["python3", "/opt/app/rogue_worker.py"], check=True)

if __name__ == "__main__":
    setup()
