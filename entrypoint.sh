#!/bin/bash
set -e

SIGNAL_DIR="/root/.local/share/signal-cli"
DATA_DIR="$SIGNAL_DIR/data"

mkdir -p "$SIGNAL_DIR"
mkdir -p "$DATA_DIR"

#-----------------------
#Step 1 - Check basic .env variables and apply defaults if necessary (except SIGNAL_GROUP_ID and MESH_DEVICE)
#-----------------------

#-----------------------
#Pre-check — detect if any Step 1 variables are missing/invalid
#-----------------------

STEP1_ISSUES=false

# TZ missing
if [ -z "$TZ" ] || [ ! -f "/usr/share/zoneinfo/$TZ" ]; then
  STEP1_ISSUES=true
fi

# SIGNAL_POLL_INTERVAL invalid
if ! [[ "$SIGNAL_POLL_INTERVAL" =~ ^[0-9]+$ ]]; then
  STEP1_ISSUES=true
fi

# LOG_LEVEL invalid
case "${LOG_LEVEL^^}" in
  DEBUG|INFO|WARNING|ERROR|CRITICAL) ;;
  *) STEP1_ISSUES=true ;;
esac

# SIGNAL_SHORT_NAMES invalid
case "${SIGNAL_SHORT_NAMES,,}" in
  true|false) ;;
  *) STEP1_ISSUES=true ;;
esac

# MESH_CHANNEL_INDEX invalid
if ! [[ "$MESH_CHANNEL_INDEX" =~ ^[0-9]+$ ]]; then
  STEP1_ISSUES=true
fi

# NODE_DB_WARMUP invalid
if ! [[ "$NODE_DB_WARMUP" =~ ^[0-9]+$ ]]; then
  STEP1_ISSUES=true
fi

# Print banner once if anything is wrong
if [ "$STEP1_ISSUES" = true ]; then
  echo ""
  echo "----------------------------------------"
  echo -e "\033[33m MISSING OR INVALID VARIABLES DETECTED\033[0m"
  echo " Applying some defaults"
  echo "----------------------------------------"
  echo ""
fi
#------------

sleep .5

# ---- SIGNAL_POLL_INTERVAL ----
if ! [[ "$SIGNAL_POLL_INTERVAL" =~ ^[0-9]+$ ]]; then
  export SIGNAL_POLL_INTERVAL=2
  echo "SIGNAL_POLL_INTERVAL is missing or invalid. Defaulting to 2."
fi

# ---- LOG_LEVEL ----
case "${LOG_LEVEL^^}" in
  DEBUG|INFO|WARNING|ERROR|CRITICAL)
    export LOG_LEVEL="${LOG_LEVEL^^}"
    ;;
  *)
    export LOG_LEVEL=INFO
    echo "LOG_LEVEL is missing or invalid. Defaulting to INFO."
    ;;
esac

# ---- SIGNAL_SHORT_NAMES ----
case "${SIGNAL_SHORT_NAMES,,}" in
  true|false)
    export SIGNAL_SHORT_NAMES="${SIGNAL_SHORT_NAMES,,}"
    ;;
  *)
    export SIGNAL_SHORT_NAMES=true
    echo "SIGNAL_SHORT_NAMES is missing or invalid. Defaulting to true."
    ;;
esac

# ---- MESH_CHANNEL_INDEX ----
if ! [[ "$MESH_CHANNEL_INDEX" =~ ^[0-9]+$ ]]; then
  export MESH_CHANNEL_INDEX=1
  echo "MESH_CHANNEL_INDEX is missing or invalid. Defaulting to 1."
fi

# ---- NODE_DB_WARMUP ----
if ! [[ "$NODE_DB_WARMUP" =~ ^[0-9]+$ ]]; then
  export NODE_DB_WARMUP=10
  echo "NODE_DB_WARMUP is missing or invalid. Defaulting to 10."
fi

# ---- TZ ----
if [ -z "$TZ" ] || [ ! -f "/usr/share/zoneinfo/$TZ" ]; then
  export TZ="America/Chicago"
  echo "TZ is missing or invalid. Defaulting to America/Chicago."
  echo "Common US options:"
  echo " America/New_York"
  echo " America/Chicago"
  echo " America/Denver"
  echo " America/Los_Angeles"
  echo ""
fi

echo ""

sleep 1

#-----------------------
#Step 2 — Check if Signal account is linked, and if not, initiate linking
#-----------------------

check_signal_linked() {
if [ -f "$DATA_DIR/accounts.json" ]; then
if grep -q '"accounts"[[:space:]]:[[:space:]][[[:space:]]*{' "$DATA_DIR/accounts.json"; then
return 0
fi
fi
return 1
}

#-----------------------
#Signal account linking if not linked
#-----------------------

if ! check_signal_linked; then
echo -e "\033[33mNo Signal account linked.\033[0m"
echo ""
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
else
echo ""
echo "QR code expired or not scanned."
echo "Please restart the container to generate a new QR code and try again."
echo ""
tail -f /dev/null
fi
fi

sleep 1

#-----------------------
#STEP 3 — Validate SIGNAL_GROUP_ID and MESH_DEVICE .env variables
#-----------------------

NEEDS_GROUP=false
NEEDS_MESH=false

#---- SIGNAL_GROUP_ID ----

GROUP_EMPTY=false
GROUP_INVALID=false

GROUP_OUTPUT=$(signal-cli listGroups || true)
VALID_IDS=$(echo "$GROUP_OUTPUT" | grep '^Id:' | awk '{print $2}')

if [ -z "$SIGNAL_GROUP_ID" ]; then
  GROUP_EMPTY=true
  NEEDS_GROUP=true
elif ! echo "$VALID_IDS" | grep -Fxq "$SIGNAL_GROUP_ID"; then
  GROUP_INVALID=true
  NEEDS_GROUP=true
fi

#---- MESH_DEVICE ----

SERIAL_DEVICES=$(ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || true)

if [ -z "$MESH_DEVICE" ]; then
  NEEDS_MESH=true

elif [ ! -e "$MESH_DEVICE" ]; then
  NEEDS_MESH=true
  MESH_INVALID_REASON="Path does not exist"

elif [ ! -c "$MESH_DEVICE" ]; then
  NEEDS_MESH=true
  MESH_INVALID_REASON="Not a serial character device"

elif ! echo "$SERIAL_DEVICES" | grep -Fxq "$MESH_DEVICE"; then
  NEEDS_MESH=true
  MESH_INVALID_REASON="Not one of the detected USB serial devices"
fi

#-----------------------
#STEP 4 — If SIGNAL_GROUP_ID or MESH_DEVICE  are missing/incorrect, provide next steps
#-----------------------

if [ "$NEEDS_GROUP" = true ] || [ "$NEEDS_MESH" = true ]; then
echo "----------------------------------------"
echo " Additional setup required"
echo "----------------------------------------"
echo ""

if [ "$NEEDS_GROUP" = true ]; then
  echo -e "\033[33mSIGNAL_GROUP_ID is missing or invalid.\033[0m"
  echo ""
  echo "Available Signal groups:"
  echo ""
  echo "$GROUP_OUTPUT"
  echo ""

  if [ "$GROUP_EMPTY" = true ]; then
    echo "Copy the desired groupID into SIGNAL_GROUP_ID."
    echo ""
    echo ""
  fi

  if [ "$GROUP_INVALID" = true ]; then
    echo -e "\033[33mSIGNAL_GROUP_ID does NOT exactly match any ID above.\033[0m"
    echo "Current value: $SIGNAL_GROUP_ID"
    echo "Make sure you copied the FULL Id including first and last characters."
    echo ""
    echo ""
  fi
fi


if [ "$NEEDS_MESH" = true ]; then
  echo -e "\033[33mMESH_DEVICE is missing or invalid.\033[0m"
  echo ""

  # If user provided something, explain why it's wrong
  if [ -n "$MESH_DEVICE" ]; then
    echo "Current value: $MESH_DEVICE"
    echo "Reason: $MESH_INVALID_REASON"
    echo ""
  fi

  echo "Detected serial devices:"
  echo ""

  SERIAL_DEVICES=$(ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || true)

  if [ -n "$SERIAL_DEVICES" ]; then
    echo "$SERIAL_DEVICES"
    echo ""
    echo "Set MESH_DEVICE to one of the paths shown above"
    echo "Example: /dev/ttyACM0, /dev/ttyUSB1, etc."
  else
    echo "(No serial devices detected)"
  fi

  echo ""
  echo ""
fi

echo -e "\033[33mFix the above variable(s) in your .env file and rebuild the container.\033[0m"
tail -f /dev/null
fi

sleep 1

#-----------------------
#STEP 5 — Bridge startup
#-----------------------

# Silence signal-cli internal logging
#export SIGNAL_CLI_OPTS="-Dorg.slf4j.simpleLogger.defaultLogLevel=error"

#  2>/dev/null 2>&1 &

signal-cli daemon \
  --http 0.0.0.0:8080 \
  --receive-mode manual \
  --no-receive-stdout \
  --ignore-attachments \
  --ignore-stories \
  2>/dev/null &

sleep 3

exec python -u /bridge/bridge.py