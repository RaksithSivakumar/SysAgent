FROM python:3.11-slim

WORKDIR /app

# Install system dependencies that collectors might use
RUN apt-get update && apt-get install -y --no-install-recommends \
    smartmontools \
    pciutils \
    dmidecode \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml setup.cfg ./
COPY sysagent/ ./sysagent/
COPY docs/README.md ./docs/README.md

RUN pip install --no-cache-dir .

ENTRYPOINT ["sysagent"]
CMD ["scan"]
