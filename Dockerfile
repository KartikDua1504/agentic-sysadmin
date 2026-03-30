FROM python:3.10-slim

# Install the Docker CLI
RUN apt-get update && \
    apt-get install -y docker.io curl && \
    rm -rf /var/lib/apt/lists/*

# Set our workspace directory
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire framework
COPY . .

CMD ["python", "inference.py"]
