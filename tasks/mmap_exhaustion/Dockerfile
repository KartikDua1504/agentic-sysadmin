# Linux Ubuntu Image (LTS)
FROM ubuntu:22.04

# Install Essentials
RUN apt-get update && apt-get install -y \
    g++ \
    strace \
    procps \
    libpam-modules \
    file \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/quant

# Copy tick_parser.cpp from Host
COPY tasks/mmap_exhaustion/tick_parser.cpp /tmp/tick_parser.cpp
RUN g++ -O3 /tmp/tick_parser.cpp -o /opt/quant/tick_parser
RUN rm /tmp/tick_parser.cpp

RUN useradd -m -s /bin/bash quant_user
RUN chown quant_user:quant_user /opt/quant/tick_parser

RUN echo "quant_user hard as 512000" >> /etc/security/limits.conf
RUN echo "quant_user soft as 512000" >> /etc/security/limits.conf

RUN grep -q "pam_limits.so" /etc/pam.d/su || echo "session required pam_limits.so" >> /etc/pam.d/su

WORKDIR /root
CMD ["/bin/bash"]
