# Linux Ubuntu Image (LTS)
FROM ubuntu:22.04

# Install Essentials
RUN apt-get update && apt-get install -y \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash deploy
RUN mkdir -p /home/deploy/.ssh
RUN echo "ssh-rsa AAAAB3NzaC1... dummy-key" > /home/deploy/.ssh/authorized_keys

# Wide open permissions
RUN chmod 777 /home/deploy/.ssh
RUN chmod 777 /home/deploy/.ssh/authorized_keys

WORKDIR /root
CMD ["/bin/bash"]
