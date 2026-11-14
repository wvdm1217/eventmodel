#!/bin/bash
set -e

# UV installation
echo "Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh


# Install NATS server
curl -sf https://binaries.nats.dev/nats-io/nats-server/v2@latest | sh
sudo mv nats-server /usr/local/bin/
curl -sf https://binaries.nats.dev/nats-io/natscli/nats@latest | sh
sudo mv nats /usr/local/bin/

echo "Post-create tasks completed."
