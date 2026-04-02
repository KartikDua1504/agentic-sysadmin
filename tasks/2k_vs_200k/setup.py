"""
Setup script for the "2k_vs_200k" task.

This script prepares a faulty system state directly on the container's root filesystem.
It installs a healthcheck service and injects a failure mechanism via ld.so.preload.

Key behavior:
- Deploys a simulated microservice healthcheck at /opt/app/healthcheck.py
- Introduces intermittent network failures via a preload hook
- Mimics real-world debugging scenarios (e.g., flaky dependencies, hidden system-level interference)

Important:
- This script modifies critical system paths (e.g., /etc/ld.so.preload)
- Intended for controlled evaluation environments only
- Must be paired with a corresponding grader that detects proper remediation

Goal for the agent:
- Identify that failures are caused by a malicious/incorrect preload
- Remove or fix /etc/ld.so.preload to restore system stability
"""

import os
import textwrap
from pathlib import Path

def write_text(path: str, content: str) -> None:
    # Utility: safely create parent dirs and write file content
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

def setup():
    # Mutates live container filesystem to create failure scenario
    print("Setting up 2k_vs_200k directly on /...")

    healthcheck_py = textwrap.dedent("""\
        #!/usr/bin/env python3
        from pathlib import Path
        import sys

        PRELOAD = Path("/etc/ld.so.preload")

        def chaos_active() -> bool:
            return PRELOAD.exists() and PRELOAD.read_text(encoding="utf-8").strip() != ""

        def simulated_probe(attempt: int) -> bool:
            if not chaos_active():
                return True
            return (attempt % 10) not in {2, 5, 8}

        def main() -> int:
            success = 0
            # socket.socket and connect(("8.8.8.8", 53)) anchors here
            for i in range(10):
                if simulated_probe(i):
                    success += 1
                else:
                    print(f"Request {i} Failed: simulated connection refused")

            if success == 10:
                print("SUCCESS: Microservice is 100% stable.")
                return 0

            print(f"FATAL: Service degradation. Only {success}/10 requests succeeded.")
            return 1

        if __name__ == "__main__":
            raise SystemExit(main())
    """)
    
    write_text("/opt/app/healthcheck.py", healthcheck_py)
    os.chmod("/opt/app/healthcheck.py", 0o755)

    # Inject dynamic linker preload → causes system-wide behavior changes
    # This is the root cause the agent must discover and fix
    write_text("/etc/ld.so.preload", "/usr/local/lib/libchaos.so\n")
    write_text("/usr/local/lib/libchaos.so", "placeholder shared object for simulation\n")

if __name__ == "__main__":
    setup()
