#!/usr/bin/env python3
import os
import textwrap
from pathlib import Path

def write_text(path: str, content: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

def setup():
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

    # Inject the actual sabotage into the live container's /etc
    write_text("/etc/ld.so.preload", "/usr/local/lib/libchaos.so\n")
    write_text("/usr/local/lib/libchaos.so", "placeholder shared object for simulation\n")

if __name__ == "__main__":
    setup()
