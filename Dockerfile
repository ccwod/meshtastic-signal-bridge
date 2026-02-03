FROM python:3.11-slim

WORKDIR /bridge

# -----------------------
# System deps
# -----------------------
RUN apt-get update && apt-get install -y \
    openjdk-21-jre-headless \
    curl \
    ca-certificates \
    qrencode \
    && rm -rf /var/lib/apt/lists/*

# -----------------------
# Install signal-cli
# -----------------------
WORKDIR /opt
RUN curl -L -o signal-cli.tar.gz https://github.com/AsamK/signal-cli/releases/download/v0.13.22/signal-cli-0.13.22.tar.gz \
    && tar xf signal-cli.tar.gz \
    && ln -s /opt/signal-cli-0.13.22/bin/signal-cli /usr/local/bin/signal-cli

# -----------------------
# Python deps
# -----------------------
RUN pip install --no-cache-dir meshtastic pyyaml pyserial

# -----------------------
# PATCH: disable exclusive serial lock
# -----------------------
RUN sed -i 's/exclusive=True/exclusive=False/g' \
    /usr/local/lib/python3.11/site-packages/meshtastic/serial_interface.py

# -----------------------
# App
# -----------------------
WORKDIR /bridge
COPY bridge /bridge
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]