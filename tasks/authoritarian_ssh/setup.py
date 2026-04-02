"""
Setup script for the "authoritarian_ssh" task.

This script provisions a misconfigured SSH environment directly on the container.

Scenario:
- SSH public key authentication is enabled with StrictModes enforced
- The deploy user's SSH directory and keys have insecure permissions
- SSH refuses authentication due to overly permissive file modes

Key elements:
- Realistic users: deploy (target), admin (noise)
- Fake auth.log entries to simulate debugging signals
- SSH config enforcing strict permission checks

Actual bug:
- /home/deploy/.ssh and authorized_keys are set to 0777 (too permissive)

Expected fix:
- Restrict permissions to:
    ~/.ssh → 700
    authorized_keys → 600

Important:
- This script mutates real system paths (/home, /etc, /var/log)
- Designed for controlled evaluation environments only
"""

import os
import subprocess

def setup():
    print("Setting up authoritarian_ssh directly on /...")

    # 1. Create the user so permissions and ownership look authentic
    subprocess.run(["useradd", "-m", "deploy"], stderr=subprocess.DEVNULL, check=False)
    subprocess.run(["useradd", "-m", "admin"], stderr=subprocess.DEVNULL, check=False)

    ssh_dir = "/home/deploy/.ssh"
    os.makedirs(ssh_dir, exist_ok=True)
    os.makedirs("/etc/ssh", exist_ok=True)
    os.makedirs("/var/log", exist_ok=True)

    # 2. Add Red Herrings (Fake logs and configs to distract)
    # Append to the real auth.log
    with open("/var/log/auth.log", "a") as f:
        f.write("Mar 31 10:00:01 server sshd[1234]: Invalid user admin from 192.168.1.5\n")
        f.write("Mar 31 10:05:22 server sshd[1235]: Connection closed by authenticating user deploy 10.0.0.2\n")
        f.write("Mar 31 10:06:00 server sshd[1236]: Authentication refused: bad ownership or modes for directory /home/deploy\n")

    with open("/etc/ssh/sshd_config", "w") as f:
        f.write("PermitRootLogin no\nPasswordAuthentication no\nPubkeyAuthentication yes\nStrictModes yes\n")

    # 3. Setup the broken SSH keys
    auth_keys = f"{ssh_dir}/authorized_keys"
    with open(auth_keys, "w") as f:
        f.write("ssh-rsa AAAAB3NzaC1... dummy-key deploy@pipeline\n")

    # Set realistic ownership
    subprocess.run(["chown", "-R", "deploy:deploy", "/home/deploy"], check=False)
    # Root Cause : Overly permissive permissions (violates SSH StrictModes)
    os.chmod(ssh_dir, 0o777)
    os.chmod(auth_keys, 0o777)

if __name__ == "__main__":
    setup()
