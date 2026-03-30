# Linux Ubuntu Image (LTS)
FROM ubuntu:22.04

# Install Essentials
RUN apt-get update && apt-get install -y python3 systemd psmisc sudo && rm -rf /var/lib/apt/lists/*

# Setup : Added Non-sudo user and created directories
RUN useradd -m -s /bin/bash mathuser
RUN mkdir -p /opt/math_daemon
RUN mkdir -p /var/lib/math_daemon && chown root:root /var/lib/math_daemon

# Copy daemon.py
COPY tasks/math_is_not_mathing/daemon.py /opt/math_daemon/daemon.py

# Bootstraps service runtime environment and handles controlled daemon startup.
RUN echo '#!/bin/bash' > /usr/local/bin/start-math.sh && \
    echo 'python3 daemon.py' >> /usr/local/bin/start-math.sh && \
    chmod +x /usr/local/bin/start-math.sh

# Systemd Env & Tmpfiles
RUN echo 'SOCKET_DIR=/run/math_daemon' > /etc/default/math-daemon && \
    echo 'DATA_DIR=/var/lib/math_daemon' >> /etc/default/math-daemon

# Creates the socket directory owned by root instead of mathuser
RUN echo 'd /run/math_daemon 0755 root root -' > /usr/lib/tmpfiles.d/math-daemon.conf

#
# The Boot Simulator
RUN echo '#!/bin/bash' > /usr/local/bin/boot_service.sh && \
    echo 'systemd-tmpfiles --create /usr/lib/tmpfiles.d/math-daemon.conf 2>/dev/null' >> /usr/local/bin/boot_service.sh && \
    echo 'set -a; source /etc/default/math-daemon; set +a' >> /usr/local/bin/boot_service.sh && \
    echo 'su - mathuser -c "env SOCKET_DIR=$SOCKET_DIR DATA_DIR=$DATA_DIR /usr/local/bin/start-math.sh"' >> /usr/local/bin/boot_service.sh && \
    chmod +x /usr/local/bin/boot_service.sh

WORKDIR /root
CMD ["tail", "-f", "/dev/null"]
