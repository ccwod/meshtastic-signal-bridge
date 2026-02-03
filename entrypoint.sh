#!/bin/bash
set -e

SIGNAL_DIR="/root/.local/share/signal-cli"
DATA_DIR="$SIGNAL_DIR/data"

mkdir -p "$SIGNAL_DIR"
mkdir -p "$DATA_DIR"

export SIGNAL_POLL_INTERVAL="${SIGNAL_POLL_INTERVAL:-2}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# ---- TZ ----
if [ -z "$TZ" ]; then
  export TZ="America/Chicago"
  echo "TZ not set → defaulting to America/Chicago"
  echo "Common US options:"
  echo "  America/New_York"
  echo "  America/Chicago"
  echo "  America/Denver"
  echo "  America/Los_Angeles"
elif [ ! -f "/usr/share/zoneinfo/$TZ" ]; then
  echo "Invalid TZ: $TZ"
  echo "Common US options:"
  echo "  America/New_York"
  echo "  America/Chicago"
  echo "  America/Denver"
  echo "  America/Los_Angeles"
  tail -f /dev/null
fi

# ---- SIGNAL_POLL_INTERVAL ----
if ! [[ "$SIGNAL_POLL_INTERVAL" =~ ^[0-9]+$ ]]; then
  export SIGNAL_POLL_INTERVAL=2
  echo "SIGNAL_POLL_INTERVAL invalid → defaulting to 2"
fi

# ---- LOG_LEVEL ----
case "${LOG_LEVEL^^}" in
  DEBUG|INFO|WARNING|ERROR|CRITICAL)
    export LOG_LEVEL="${LOG_LEVEL^^}"
    ;;
  *)
    export LOG_LEVEL=INFO
    echo "LOG_LEVEL invalid → defaulting to INFO"
    ;;
esac

# ---- SIGNAL_SHORT_NAMES ----
case "${SIGNAL_SHORT_NAMES,,}" in
  true|false)
    export SIGNAL_SHORT_NAMES="${SIGNAL_SHORT_NAMES,,}"
    ;;
  *)
    export SIGNAL_SHORT_NAMES=true
    echo "SIGNAL_SHORT_NAMES invalid → defaulting to true"
    ;;
esac

# ---- MESH_CHANNEL_INDEX ----
if ! [[ "$MESH_CHANNEL_INDEX" =~ ^[0-9]+$ ]]; then
  export MESH_CHANNEL_INDEX=1
  echo "MESH_CHANNEL_INDEX invalid → defaulting to 1"
fi

# ---- NODE_DB_WARMUP ----
if ! [[ "$NODE_DB_WARMUP" =~ ^[0-9]+$ ]]; then
  export NODE_DB_WARMUP=10
  echo "NODE_DB_WARMUP invalid → defaulting to 10"
fi

echo ""


# -----------------------
# Helper — check if Signal is actually linked
# -----------------------
check_signal_linked() {
  if [ -f "$DATA_DIR/accounts.json" ]; then
    if grep -q '"accounts"[[:space:]]*:[[:space:]]*\[[[:space:]]*{' "$DATA_DIR/accounts.json"; then
      return 0
    fi
  fi
  return 1
}

# -----------------------
# STEP 1 — Signal account linking
# -----------------------

if ! check_signal_linked; then
  echo "No Signal account linked."
  echo ""

  while true; do
    echo "Scan this QR code in Signal:"
    echo "Signal App → Settings → Linked Devices → Link New Device"
    echo ""

    signal-cli link -n "Mesh Bridge" | tee >(xargs -L 1 qrencode -t utf8)

    echo ""
    echo "Checking if account linked..."

    if check_signal_linked; then
      echo ""
      echo "Signal account linked successfully."
      echo ""
      break
    else
      echo ""
      echo "QR code expired or not scanned."
      echo ""
      echo "Please restart the container to generate a new QR code and try again."
      echo ""
      tail -f /dev/null
    fi
  done
fi

# -----------------------
# STEP 2 — Check for missing SIGNAL_GROUP_ID
# -----------------------

if [ -z "$SIGNAL_GROUP_ID" ]; then
  echo "SIGNAL_GROUP_ID is empty."
  echo ""
  echo "Available Signal groups:"
  echo ""
  signal-cli listGroups || true
  echo ""
  echo "Copy the desired groupId into SIGNAL_GROUP_ID."
  echo ""
  echo "Update variables and rebuild container."
  echo ""
  tail -f /dev/null
fi

# -----------------------
# STEP 3 — Now validate SIGNAL_GROUP_ID (it exists)
# -----------------------

GROUP_OUTPUT=$(signal-cli listGroups || true)

VALID_IDS=$(echo "$GROUP_OUTPUT" | grep '^Id:' | awk '{print $2}')

if ! echo "$VALID_IDS" | grep -Fxq "$SIGNAL_GROUP_ID"; then
  echo "$GROUP_OUTPUT"
  echo ""
  echo "ERROR: SIGNAL_GROUP_ID does NOT exactly match any group above."
  echo "SIGNAL_GROUP_ID: $SIGNAL_GROUP_ID"
  echo ""
  echo "Make sure you copied the FULL ID including first and last characters."
  echo ""
  echo "Update variable and rebuild container."
  echo ""
  tail -f /dev/null
fi

# -----------------------
# STEP 4 — Check MESH_DEVICE
# -----------------------

if [ -z "$MESH_DEVICE" ]; then
  echo "MESH_DEVICE is empty."
  echo ""
  echo "Detected serial devices:"
  echo ""

  SERIAL_DEVICES=$(ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || true)

  if [ -n "$SERIAL_DEVICES" ]; then
    echo "$SERIAL_DEVICES"
    echo ""
    echo "Set MESH_DEVICE to correct path (example: /dev/ttyACM0)."
  else
    echo "(No serial devices detected)"
  fi

  echo ""
  echo "Update variable and rebuild container."
  echo ""
  tail -f /dev/null
fi

# -----------------------
# STEP 5 — Normal startup
# -----------------------

signal-cli daemon \
  --http 0.0.0.0:8080 \
  --receive-mode manual \
  --no-receive-stdout \
  --ignore-attachments \
  --ignore-stories \
  2>/dev/null &

sleep 3

exec python -u /bridge/bridge.py
