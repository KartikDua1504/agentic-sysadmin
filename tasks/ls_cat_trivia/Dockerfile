# Linux Ubuntu Image (LTS)
FROM ubuntu:22.04

# Install Essentials
RUN apt-get update && apt-get install -y curl coreutils grep bash \
    && rm -rf /var/lib/apt/lists/*

# Create the malicious silent wrappers
RUN echo '#!/bin/bash' > /usr/local/bin/ls && echo 'exit 0' >> /usr/local/bin/ls && chmod +x /usr/local/bin/ls
RUN echo '#!/bin/bash' > /usr/local/bin/cat && echo 'exit 0' >> /usr/local/bin/cat && chmod +x /usr/local/bin/cat
RUN echo '#!/bin/bash' > /usr/local/bin/grep && echo 'exit 1' >> /usr/local/bin/grep && chmod +x /usr/local/bin/grep

# Create the legitimate script
RUN echo '#!/bin/bash' > /usr/local/bin/legit_tool && \
    echo 'echo "I am a critical production script!"' >> /usr/local/bin/legit_tool && \
    chmod +x /usr/local/bin/legit_tool

# Fake Curl Response for the task to prevent downloads and to isolate the task
RUN echo '#!/bin/bash' > /usr/local/bin/curl && \
    echo 'echo "curl: (6) Could not resolve host: $1"' >> /usr/local/bin/curl && \
    echo 'exit 6' >> /usr/local/bin/curl && \
    chmod +x /usr/local/bin/curl

WORKDIR /root
CMD ["/bin/bash"]
