# Linux Ubuntu Image (LTS)
FROM ubuntu:22.04

# Install Essentials
RUN apt-get update && apt-get install -y \
    gcc \
    ltrace \
    strace \
    python3 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/app

# Runtime interposition layer modifying outbound socket behavior for fault simulation.
RUN printf '%s\n' \
'#define _GNU_SOURCE' \
'#include <dlfcn.h>' \
'#include <sys/socket.h>' \
'#include <errno.h>' \
'#include <stdlib.h>' \
'int connect(int sockfd, const struct sockaddr *addr, socklen_t addrlen) {' \
'    int (*orig_connect)(int, const struct sockaddr *, socklen_t) = dlsym(RTLD_NEXT, "connect");' \
'    if (rand() % 3 == 0) {' \
'        errno = ECONNREFUSED;' \
'        return -1;' \
'    }' \
'    return orig_connect(sockfd, addr, addrlen);' \
'}' > /opt/app/libchaos.c

RUN gcc -shared -fPIC -o /usr/local/lib/libchaos.so /opt/app/libchaos.c -ldl

RUN echo "/usr/local/lib/libchaos.so" > /etc/ld.so.preload

# Lightweight probe for outbound connectivity consistency. 
RUN printf '%s\n' \
'import socket' \
'import sys' \
'success = 0' \
'for i in range(10):' \
'    try:' \
'        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)' \
'        s.settimeout(1)' \
'        s.connect(("8.8.8.8", 53))' \
'        s.close()' \
'        success += 1' \
'    except Exception as e:' \
'        print(f"Request {i} Failed: {e}")' \
'if success == 10:' \
'    print("SUCCESS: Microservice is 100% stable.")' \
'    sys.exit(0)' \
'else:' \
'    print(f"FATAL: Service degradation. Only {success}/10 requests succeeded.")' \
'    sys.exit(1)' > /opt/app/healthcheck.py

WORKDIR /root
CMD ["/bin/bash"]
