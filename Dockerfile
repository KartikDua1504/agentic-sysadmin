FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Core system + debugging + networking + misdirection tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Standard Python & Build
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    gcc \
    g++ \
    make \
    # Low-level debugging
    gdb \
    strace \
    ltrace \
    # Sysadmin core
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
    # Networking
    iproute2 \
    net-tools \
    dnsutils \
    iputils-ping \
    openssh-client \
    ca-certificates \
    tzdata \
    # Misdirection & Red Herrings
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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

# Run the app.py server to keep the HF Space alive and respond to OpenEnv pings
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
