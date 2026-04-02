# Base image: stable Ubuntu LTS for reproducible sysadmin environment
FROM ubuntu:22.04

# Disable interactive prompts + ensure clean Python output
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
# Grouped by purpose for clarity and maintainability
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Python runtime + build tooling
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    gcc \
    g++ \
    make \
    \
    # Low-level debugging / tracing (used by tasks)
    gdb \
    strace \
    ltrace \
    \
    # Core sysadmin utilities (baseline environment)
    lsof \
    procps \
    util-linux \
    coreutils \
    file \
    curl \
    wget \
    git \
    vim-tiny \
    less \
    sudo \
    libpam-modules \
    psmisc \
    systemd \
    \
    # Networking tools (diagnostics + failure scenarios)
    iproute2 \
    net-tools \
    dnsutils \
    iputils-ping \
    openssh-client \
    ca-certificates \
    tzdata \
    \
    # Intentional noise / red herrings for agent robustness testing
    cowsay \
    fortune \
    sl \
    ed \
    jq \
    nmap \
    tcpdump \
    htop \
    tree \
    tmux \
    neofetch \
    \
    # Cleanup to reduce image size
    && rm -rf /var/lib/apt/lists/*

# Application working directory
WORKDIR /app

# Install Python dependencies separately to leverage Docker layer caching
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy full project (tasks, env, server, etc.)
COPY . .

# Expose port used by FastAPI + Gradio app
EXPOSE 7860

# Start ASGI server (serves both API + UI)
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
