#!/usr/bin/env bash
set -euo pipefail

CONFIG_DIR="${1:-}"
IMAGE="${IMAGE:-ghcr.io/home-assistant/home-assistant:stable}"
HOST_PORT="${HOST_PORT:-8500}"
CONTAINER_PORT="${CONTAINER_PORT:-8123}"
CONTAINER_NAME="homeassistant-yamaha-test"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MEDIA_PLAYER_PATH="$SCRIPT_DIR/media_player.py"
RXV_DIR="$SCRIPT_DIR/rxv"
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

if [[ ! -f "$MEDIA_PLAYER_PATH" ]]; then
  echo "Patched media_player.py not found: $MEDIA_PLAYER_PATH"
  exit 1
fi

if [[ ! -d "$RXV_DIR" ]]; then
  echo "Patched rxv directory not found: $RXV_DIR"
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

existing_8500_containers="$(docker ps --filter publish=8500 --format '{{.ID}}')"
if [[ -n "$existing_8500_containers" ]]; then
  echo "Stopping containers publishing host port 8500: $existing_8500_containers"
  docker rm -f $existing_8500_containers >/dev/null
fi

if docker ps -a --format '{{.Names}}' | grep -Fxq "$CONTAINER_NAME"; then
  docker rm -f "$CONTAINER_NAME" >/dev/null || true
fi

echo "Using Home Assistant config directory: $TMP_CONFIG_DIR"
echo "Using override config from: $OVERRIDE_CONFIG_PATH"
echo "Mounting rxv package from: $RXV_DIR"
echo "Listening on host port $HOST_PORT and container port $CONTAINER_PORT"

docker run --rm -d \
  --name "$CONTAINER_NAME" \
  -e PYTHONPATH="/opt/yamaha_override/rxv${PYTHONPATH:+:$PYTHONPATH}" \
  -p "$HOST_PORT:$CONTAINER_PORT" \
  -v "$TMP_CONFIG_DIR:/config" \
  -v "$MEDIA_PLAYER_PATH:/usr/src/homeassistant/homeassistant/components/yamaha/media_player.py:ro" \
  -v "$RXV_DIR:/opt/yamaha_override/rxv:ro" \
  "$IMAGE" >/dev/null

docker logs -f "$CONTAINER_NAME" &
LOGS_PID=$!
wait "$LOGS_PID"
