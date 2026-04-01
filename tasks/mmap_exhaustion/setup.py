#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

def setup():
    print("Setting up mmap_exhaustion directly on /...")

    # 1. Create the user
    subprocess.run(["useradd", "-m", "-s", "/bin/bash", "quant_user"], stderr=subprocess.DEVNULL, check=False)

    # 2. Compile the parser directly into the system
    os.makedirs("/opt/quant", exist_ok=True)
    
    # We run setup.py from the repository root, so this path is relative to repo root
    cpp_path = Path("tasks/mmap_exhaustion/tick_parser.cpp").resolve()
    bin_path = "/opt/quant/tick_parser"

    subprocess.run(["g++", "-O3", str(cpp_path), "-o", bin_path], check=True)
    subprocess.run(["chown", "quant_user:quant_user", bin_path], check=True)

    # 3. Apply the sabotage (Address Space limits)
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
