FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y ca-certificates curl gnupg lsb-release \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list > /dev/null


RUN apt-get update && apt-get install -y --no-install-recommends \
    git openssh-client \
    python3 python3-venv python3-pip \
    build-essential pkg-config \
    jq ripgrep fd-find unzip \
    nodejs \
    docker.io docker-compose-plugin \
  && rm -rf /var/lib/apt/lists/*

RUN npm install -g @openai/codex@latest @kilocode/cli@latest @fission-ai/openspec@latest opencode-ai

RUN useradd -m -s /bin/bash dev && \
    usermod -aG docker dev || true

USER dev
WORKDIR /home/dev
ENV PATH="/home/dev/.local/bin:${PATH}"

WORKDIR /workspace
CMD ["/bin/bash"]
