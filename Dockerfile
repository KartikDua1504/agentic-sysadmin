# ==========================================================================
# Agentic Sysadmin — Container Image
#
# Base:    Ubuntu 22.04 LTS (stable, reproducible package set)
# Purpose: Provides a realistic Linux environment where AI agents must
#          diagnose and repair deliberately broken system configurations.
#
# The image ships with a broad set of sysadmin tools so that the agent
# has everything it needs — plus deliberate "noise" packages (cowsay,
# fortune, sl) that test the agent's ability to stay focused.
# ==========================================================================

FROM ubuntu:22.04

# -- Build-time configuration ---------------------------------------------
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# -- System packages -------------------------------------------------------
# Grouped by purpose for maintainability.  Each group is documented so
# that reviewers can understand why every package is present.
RUN apt-get update && apt-get install -y --no-install-recommends \
    # --- Python runtime and native extension build chain ---
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python-is-python3 \
    build-essential \
    gcc \
    g++ \
    make \
    \
    # --- Low-level debugging and tracing (required by tasks) ---
    gdb \
    strace \
    ltrace \
    \
    # --- Core sysadmin utilities (baseline toolset) ---
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
    # --- Networking diagnostics ---
    iproute2 \
    net-tools \
    dnsutils \
    iputils-ping \
    openssh-client \
    openssh-server \
    ca-certificates \
    tzdata \
    \
    # --- Noise / red-herring packages (agent robustness testing) ---
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
    && rm -rf /var/lib/apt/lists/*

# -- Application directory -------------------------------------------------
WORKDIR /app

# -- Python dependencies ---------------------------------------------------
# Copied separately from the rest of the source to leverage Docker's
# build cache: re-installing deps only when requirements.txt changes.
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# -- Application source ----------------------------------------------------
COPY . .

# -- Network ---------------------------------------------------------------
# Port 7860 is the Hugging Face Spaces default for custom containers.
EXPOSE 7860

# -- Entry point ------------------------------------------------------------
# Start the OpenEnv-compliant ASGI server.
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
