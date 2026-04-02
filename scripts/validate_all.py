"""
Validation harness for Agentic Sysadmin tasks.

This script replays known-good solution trajectories (command sequences)
against each task environment to verify correctness of:

- Environment setup (reset scripts)
- Task configuration (filesystem, services, constraints)
- Grader logic (reward + termination conditions)

Each task must:
- Reach `done = True`
- Achieve `score = 1.0`

If any task fails, the script exits immediately.

Usage:
    python validate.py [task_name]

Purpose:
- Sanity-check tasks before running LLM agents
- Prevent debugging agent failures caused by broken environments
"""
import sys
import os
import argparse

# Ensure project root is in path for module resolution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env.core import LinuxAdminEnv
from env.models import SysAdminAction

def run_validation(target_task=None):
    """
    Execute predefined solution trajectories against tasks to validate correctness.

    Each task maps to a sequence of shell commands representing a known-good solution.
    The environment executes these commands step-by-step and verifies:
    - Final reward == 1.0
    - Task marked as done by grader

    Args:
        target_task (str, optional): If provided, only this task is validated.
    """
    solutions = {
        "mmap_exhaustion": [
            # Diagnose mmap failure under constrained limits
            "su - quant_user -c '/opt/quant/tick_parser'",
            "strace -e mmap su - quant_user -c '/opt/quant/tick_parser' 2>&1 | tail -n 20",
            # Fix limits configuration
            "sed -i '/^quant_user/d' /etc/security/limits.conf",
            "cat /etc/security/limits.conf | grep quant_user",
            # Verify fix
            "su - quant_user -c '/opt/quant/tick_parser'"
        ],
        "ls_cat_trivia": [
            # 1. Agent gets tricked by the fake DNS error
            "curl https://google.com",
            # 2. Agent tries to check DNS settings, but `cat` is silent
            "cat /etc/resolv.conf",
            # 3. Agent gets suspicious, checks binaries using absolute paths
            "which curl",
            "/bin/ls -la /usr/local/bin",
            # 4. Agent assassinates the imposters using the absolute path to `rm`
           "/bin/rm -f /usr/local/bin/curl /usr/local/bin/ls /usr/local/bin/cat /usr/local/bin/grep",
            # 5. Agent proves the system is healed
            "curl --version"
        ],
        "authoritarian_ssh": [
            # 1. Agent suspects an SSH strict modes issue and inspects the deploy user's directory permissions
            "ls -la /home/deploy/.ssh",
            # 2. Agent realizes the .ssh directory is too open and restricts it to owner-only (sshd strict requirement)
            "chmod 700 /home/deploy/.ssh",
            # 3. Agent secures the authorized_keys file so no other users can read or append malicious keys
            "chmod 600 /home/deploy/.ssh/authorized_keys"
        ],
        "pls_adopt_me": [
            # 1. Agent gets the error and checks the PID file
            "/usr/local/bin/start_app.sh",
            "cat /opt/app/app.pid",
            # 2. Agent realizes the PID is dead, checks for actual file locks
            "lsof /opt/app/production.db",
            # 3. Agent kills the orphan and successfully starts the app
            "kill -9 $(lsof -t /opt/app/production.db)",
            "/usr/local/bin/start_app.sh"
        ],
        "2k_vs_200k": [
            # 1. Run the script, see intermittent failures
            "python3 /opt/app/healthcheck.py",
            # 2. Trace the system calls to realize libc is returning the error natively
            "strace -e connect python3 /opt/app/healthcheck.py",
            # 3. Check what shared libraries are being loaded into the python binary
            "ldd $(which python3)",
            # 4. Spot the global preload and destroy it
            "cat /etc/ld.so.preload",
            "rm -f /etc/ld.so.preload",
            # 5. Verify the service is stable
            "python3 /opt/app/healthcheck.py"
        ],
        "math_is_not_mathing": [
            # 1. Agent runs the boot simulator and sees the python file is missing
            "/usr/local/bin/boot_service.sh",
            # 2. Agent checks the wrapper script and fixes the relative path
            "cat /usr/local/bin/start-math.sh",
            "sed -i 's/python3 daemon.py/python3 \\/opt\\/math_daemon\\/daemon.py/' /usr/local/bin/start-math.sh",
            # 3. Agent runs again, hits a permission error on the state data directory
            "/usr/local/bin/boot_service.sh",
            "ls -ld /var/lib/math_daemon",
            "chown mathuser:mathuser /var/lib/math_daemon",
            # 4. Agent runs again, hits a permission error on the unix socket directory
            "/usr/local/bin/boot_service.sh",
            # 5. Agent checks the boot simulator to see how the socket dir is created
            "cat /usr/local/bin/boot_service.sh",
            # 6. Agent inspects the tmpfiles.d config and fixes the ownership rule
            "cat /usr/lib/tmpfiles.d/math-daemon.conf",
            "sed -i 's/root root/mathuser mathuser/' /usr/lib/tmpfiles.d/math-daemon.conf",
            # 7. Final test run proving the daemon boots successfully
            "/usr/local/bin/boot_service.sh",
        ]
    }

    # Subset of tasks if required
    if target_task:
        if target_task not in solutions:
            print(f"Error: Task '{target_task}' not found in the solutions dictionary.")
            sys.exit(1)
        tasks_to_run = {target_task: solutions[target_task]}
    else:
        tasks_to_run = solutions


    for task_name, commands in tasks_to_run.items():
        print(f"\n======================================")
        print(f"-> Testing Tier: {task_name}")
        print(f"======================================")
        
        try:
            env = LinuxAdminEnv(task_name=task_name)
            env.reset()
        except Exception as e:
            print(f"-> Failed to boot container for {task_name}. Did you run docker build?")
            print(f"Error: {e}")
            sys.exit(1)
        
        for cmd in commands:
            print(f"-> Agent runs: {cmd}")
            obs, reward, done, _ = env.step(SysAdminAction(command=cmd))
            
            if obs.exit_code != 0:
                print(f"-> Command failed with exit code {obs.exit_code}: {obs.stderr.strip()}")
            
        print(f"\n-> Final Score: {reward.score}")
        print(f"-> Task Done: {done}")
        print(f"-> Grader Reason: {reward.reasoning}")
        
        if not done or reward.score != 1.0:
            print(f"\n-> VALIDATION FAILED on {task_name}!")
            sys.exit(1)
        else:
            print(f"\n-> {task_name} PASSED!")

    print("\n-> ALL TIERS VALIDATED SUCCESSFULLY! YOU ARE READY TO RUN THE AI.")

if __name__ == "__main__":
    # CLI entry point for running validation
    parser = argparse.ArgumentParser(description="Validate agentic-sysadmin tasks.")
    parser.add_argument("task_name", nargs="?", help="Optional: Specify a single task to run (e.g., mmap_exhaustion)")
    args = parser.parse_args()

    run_validation(args.task_name)
