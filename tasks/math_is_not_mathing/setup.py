#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

def write_text(path: str, content: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

def setup():
    print("Setting up math_is_not_mathing directly on /...")

    # 1. Create the non-sudo user and directories
    subprocess.run(["useradd", "-m", "-s", "/bin/bash", "mathuser"], stderr=subprocess.DEVNULL, check=False)
    os.makedirs("/opt/math_daemon", exist_ok=True)
    
    var_lib = "/var/lib/math_daemon"
    os.makedirs(var_lib, exist_ok=True)
    subprocess.run(["chown", "root:root", var_lib], check=True) # Intentional bad permission

    # 2. Copy the Python daemon logic
    daemon_py_content = """\
import os, sys, socket
sock_dir = os.environ.get("SOCKET_DIR")
data_dir = os.environ.get("DATA_DIR")

if not sock_dir or not data_dir:
    print("FATAL: Missing environment variables SOCKET_DIR or DATA_DIR.")
    sys.exit(1)

data_path = os.path.join(data_dir, "state.dat")
try:
    with open(data_path, "w") as f: f.write("OK")
except PermissionError:
    print(f"FATAL: Permission denied to write to {data_path}")
    sys.exit(1)

sock_path = os.path.join(sock_dir, "math.sock")
try:
    if os.path.exists(sock_path): os.remove(sock_path)
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(sock_path)
except PermissionError:
    print(f"FATAL: Permission denied to bind socket at {sock_path}")
    sys.exit(1)

print("SUCCESS: Daemon booted, state saved, and socket bound!")
sys.exit(0)
"""
    write_text("/opt/math_daemon/daemon.py", daemon_py_content)

    # 3. Create the broken wrapper script (relative path error)
    start_math_sh = "#!/bin/bash\npython3 daemon.py\n"
    write_text("/usr/local/bin/start-math.sh", start_math_sh)
    os.chmod("/usr/local/bin/start-math.sh", 0o755)

    # 4. Systemd Env & Broken Tmpfiles (root ownership instead of mathuser)
    write_text("/etc/default/math-daemon", "SOCKET_DIR=/run/math_daemon\nDATA_DIR=/var/lib/math_daemon\n")
    write_text("/usr/lib/tmpfiles.d/math-daemon.conf", "d /run/math_daemon 0755 root root -\n")

    # 5. Create the Boot Simulator
    boot_service_sh = """#!/bin/bash
systemd-tmpfiles --create /usr/lib/tmpfiles.d/math-daemon.conf 2>/dev/null
set -a; source /etc/default/math-daemon; set +a
su - mathuser -c "env SOCKET_DIR=$SOCKET_DIR DATA_DIR=$DATA_DIR /usr/local/bin/start-math.sh"
"""
    write_text("/usr/local/bin/boot_service.sh", boot_service_sh)
    os.chmod("/usr/local/bin/boot_service.sh", 0o755)

if __name__ == "__main__":
    setup()
