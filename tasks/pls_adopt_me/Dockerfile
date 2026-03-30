# Linux Ubuntu Image (LTS)
FROM ubuntu:22.04

# Install Essentials
RUN apt-get update && apt-get install -y \
    lsof \
    psmisc \
    python3 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/app
RUN touch /opt/app/production.db

# Background worker simulating a long-lived process holding a file lock.
# Uses fcntl for exclusive locking and writes PID metadata for observability.
RUN echo 'import os, time, fcntl' > /opt/app/rogue_worker.py && \
    echo 'db = open("/opt/app/production.db", "w")' >> /opt/app/rogue_worker.py && \
    echo 'fcntl.flock(db, fcntl.LOCK_EX)' >> /opt/app/rogue_worker.py && \
    echo 'parent_pid = os.getpid()' >> /opt/app/rogue_worker.py && \
    echo 'with open("/opt/app/app.pid", "w") as pidfile:' >> /opt/app/rogue_worker.py && \
    echo '    pidfile.write(str(parent_pid))' >> /opt/app/rogue_worker.py && \
    echo 'if os.fork() > 0:' >> /opt/app/rogue_worker.py && \
    echo '    os._exit(0)' >> /opt/app/rogue_worker.py && \
    echo 'else:' >> /opt/app/rogue_worker.py && \
    echo '    while True: time.sleep(1)' >> /opt/app/rogue_worker.py

# Startup script with single-instance guard.
# Uses file locking on the database to avoid concurrent access and ensure consistency.
RUN echo '#!/bin/bash' > /usr/local/bin/start_app.sh && \
    echo 'exec 9>/opt/app/production.db' >> /usr/local/bin/start_app.sh && \
    echo 'if ! flock -n 9; then' >> /usr/local/bin/start_app.sh && \
    echo '  echo "FATAL: production.db is locked by another process! Check /opt/app/app.pid"' >> /usr/local/bin/start_app.sh && \
    echo '  exit 1' >> /usr/local/bin/start_app.sh && \
    echo 'fi' >> /usr/local/bin/start_app.sh && \
    echo 'echo "SUCCESS: Database lock acquired. App Booted!"' >> /usr/local/bin/start_app.sh

RUN chmod +x /usr/local/bin/start_app.sh

WORKDIR /root
CMD ["/bin/bash", "-c", "python3 /opt/app/rogue_worker.py && tail -f /dev/null"]
