# Validates env paths, writes state file, and binds a UNIX socket; fails on misconfiguration or permission errors.

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
