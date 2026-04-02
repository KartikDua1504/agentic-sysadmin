"""
Setup script for the "mmap_exhaustion" task.

This script provisions a resource-constrained environment where a process
fails due to virtual memory (address space) limits.

Scenario:
- A C++ binary (`tick_parser`) is compiled and executed as a non-root user
- The user is restricted via ulimit (address space limits)
- The binary intermittently fails due to inability to allocate memory (mmap failures)

Key mechanics:
- /etc/security/limits.conf enforces per-user resource limits
- PAM (pam_limits.so) ensures limits apply during `su` sessions

Actual bug:
- quant_user has extremely low address space limits (soft/hard as = 512000)

Expected fix:
- Remove or increase limits for quant_user in limits.conf

Important:
- This script mutates real system config (/etc/security, PAM)
- Requires PAM limits to be active for enforcement
- Designed for controlled evaluation environments only
"""

import os
import subprocess
from pathlib import Path

def setup():
    print("Setting up mmap_exhaustion directly on /...")

    # 1. Create the user
    subprocess.run(["useradd", "-m", "-s", "/bin/bash", "quant_user"], stderr=subprocess.DEVNULL, check=False)

    # 2. Compile the parser directly into the system
    os.makedirs("/opt/quant", exist_ok=True)
    
    # Run setup.py from the repository root, so this path is relative to repo root
    cpp_path = Path("tasks/mmap_exhaustion/tick_parser.cpp").resolve()
    bin_path = "/opt/quant/tick_parser"

    subprocess.run(["g++", "-O3", str(cpp_path), "-o", bin_path], check=True)
    subprocess.run(["chown", "quant_user:quant_user", bin_path], check=True)

    # Inject resource constraint via ulimit (address space restriction → mmap failures)
    limits_conf = "/etc/security/limits.conf"
    with open(limits_conf, "a") as f:
        f.write("\nquant_user hard as 512000\n")
        f.write("quant_user soft as 512000\n")

    # 4. Ensure PAM applies limits for the 'su' command
    pam_su = "/etc/pam.d/su"
    if os.path.exists(pam_su):
        with open(pam_su, "r+") as f:
            content = f.read()
            if "session required pam_limits.so" not in content:
                f.write("\nsession required pam_limits.so\n")

if __name__ == "__main__":
    setup()
