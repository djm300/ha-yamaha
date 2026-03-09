#!/usr/bin/env bash
set -euo pipefail

CONFIG_DIR="${1:-}"
IMAGE="${IMAGE:-ghcr.io/home-assistant/home-assistant:stable}"
HOST_PORT="${HOST_PORT:-8500}"
CONTAINER_PORT="${CONTAINER_PORT:-8123}"
CONTAINER_NAME="homeassistant-yamaha-test"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
YAMAHA_COMPONENT_DIR="$REPO_ROOT/homeassistant/components/yamaha"
OVERRIDE_CONFIG_PATH="$SCRIPT_DIR/configuration.yaml"
TMP_CONFIG_DIR="/tmp/ha"
TARGET_CONFIG_FILE="$TMP_CONFIG_DIR/configuration.yaml"
LOGS_PID=""

stop_container() {
  if docker ps --format '{{.Names}}' | grep -Fxq "$CONTAINER_NAME"; then
    docker stop "$CONTAINER_NAME" >/dev/null || true
  fi
}

handle_signal() {
  if [[ -n "$LOGS_PID" ]]; then
    kill "$LOGS_PID" >/dev/null 2>&1 || true
  fi
  stop_container
  exit 130
}

trap handle_signal INT TERM

if [[ -z "$CONFIG_DIR" ]]; then
  echo "Usage: $0 /path/to/ha-config"
  exit 1
fi

if [[ ! -d "$CONFIG_DIR" ]]; then
  echo "Config directory does not exist: $CONFIG_DIR"
  exit 1
fi

if [[ ! -d "$YAMAHA_COMPONENT_DIR" ]]; then
  echo "Patched yamaha component directory not found: $YAMAHA_COMPONENT_DIR"
  exit 1
fi

if [[ ! -f "$OVERRIDE_CONFIG_PATH" ]]; then
  echo "Override configuration.yaml not found: $OVERRIDE_CONFIG_PATH"
  exit 1
fi

mkdir -p "$TMP_CONFIG_DIR"
#find "$TMP_CONFIG_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
cp -a "$CONFIG_DIR"/. "$TMP_CONFIG_DIR"/
cp "$OVERRIDE_CONFIG_PATH" "$TARGET_CONFIG_FILE"

existing_host_port_containers="$(docker ps --filter "publish=$HOST_PORT" --format '{{.ID}}')"
if [[ -n "$existing_host_port_containers" ]]; then
  echo "Stopping containers publishing host port $HOST_PORT: $existing_host_port_containers"
  docker rm -f $existing_host_port_containers >/dev/null
fi

if docker ps -a --format '{{.Names}}' | grep -Fxq "$CONTAINER_NAME"; then
  docker rm -f "$CONTAINER_NAME" >/dev/null || true
fi

echo "Using Home Assistant config directory: $TMP_CONFIG_DIR"
echo "Using override config from: $OVERRIDE_CONFIG_PATH"
echo "Mounting yamaha component from: $YAMAHA_COMPONENT_DIR"
echo "Listening on host port $HOST_PORT and container port $CONTAINER_PORT"

docker run --rm -d \
  --name "$CONTAINER_NAME" \
  -p "$HOST_PORT:$CONTAINER_PORT" \
  -v "$TMP_CONFIG_DIR:/config" \
  -v "$YAMAHA_COMPONENT_DIR:/usr/src/homeassistant/homeassistant/components/yamaha:ro" \
  "$IMAGE" >/dev/null

docker logs -f "$CONTAINER_NAME" &
LOGS_PID=$!
wait "$LOGS_PID"
