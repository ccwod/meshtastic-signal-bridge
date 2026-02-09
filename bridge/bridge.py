import os
import time
import logging
import requests
from meshtastic.serial_interface import SerialInterface
from pubsub import pub
import queue
import threading

# -------------------------
# Safe env helpers
# -------------------------

def env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        print(f"{name} invalid. Using default {default}")
        return default


def env_bool(name, default):
    val = os.environ.get(name)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes")


# -------------------------
# Environment config
# -------------------------

SIGNAL_GROUP_ID = os.environ["SIGNAL_GROUP_ID"]
MESH_DEVICE = os.environ["MESH_DEVICE"]
MESH_CHANNEL_INDEX = int(os.environ["MESH_CHANNEL_INDEX"])
POLL_INTERVAL = int(os.environ["SIGNAL_POLL_INTERVAL"])
NODE_DB_WARMUP = int(os.environ["NODE_DB_WARMUP"])
SIGNAL_SHORT_NAMES = os.environ["SIGNAL_SHORT_NAMES"].lower() == "true"

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
if LOG_LEVEL not in ("DEBUG", "INFO", "WARNING", "ERROR"):
    LOG_LEVEL = "INFO"

SIGNAL_RPC_URL = "http://localhost:8080/api/v1/rpc"

PRIMARY_BLOCK_MESSAGE = (
    "[BRIDGE] Signal → Mesh relay is disabled while MESH_CHANNEL_INDEX=0 (Primary). "
    "This mode is only for testing Mesh → Signal. Please set MESH_CHANNEL_INDEX to a different channel."
)

COMMAND_PREFIX = "!"
BRIDGE_PREFIX = "BRIDGE"

# -------------------------
# Mesh message size limits
# -------------------------

MAX_MESH_BYTES = 200
TRUNCATION_SUFFIX = "…"

# -------------------------
# Runtime relay state
# -------------------------

RELAY_ENABLED = True
RELAY_MODE = 1

# -------------------------
# Logging
# -------------------------

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("bridge")

# -------------------------
# Bridge start time (used to discard old Signal messages)
# -------------------------

BRIDGE_START_TIME = int(time.time() * 1000)

# -------------------------
# Signal to Mesh message queueing
# -------------------------

MESH_TX_QUEUE = queue.Queue()

def mesh_tx_worker(iface):
    while True:
        message, sender_label, log_relay = MESH_TX_QUEUE.get()

        try:
            iface.sendText(message, channelIndex=MESH_CHANNEL_INDEX)

            if log_relay:
                if sender_label:
                    log.info(f"Relayed Signal → Mesh ({sender_label})")
                else:
                    log.info("Relayed Signal → Mesh")

        except Exception as e:
            log.error("Mesh send failed — interface may be down: %s", e)

        time.sleep(3.2)
        MESH_TX_QUEUE.task_done()


# -------------------------
# Formatting helpers
# -------------------------

def format_signal_sender_name(profile_name, phone=None):
    name = profile_name or phone or "Signal"
    if SIGNAL_SHORT_NAMES and name:
        name = name.split(" ", 1)[0]
    return name


def format_signal_to_mesh(sender_name, message_text):
    return f"[{sender_name}] {message_text}"
    
def truncate_signal_to_mesh_message(sender_name, message_text):
    """
    Returns (final_message, was_truncated)
    Ensures the final UTF-8 encoded message fits within MAX_MESH_BYTES.
    """

    prefix = f"[{sender_name}] "
    prefix_bytes = len(prefix.encode("utf-8"))

    max_body_bytes = MAX_MESH_BYTES - prefix_bytes
    if max_body_bytes <= 0:
        # Extremely long sender name; hard fail-safe
        return prefix[:MAX_MESH_BYTES], True

    body = message_text
    body_bytes = body.encode("utf-8")

    if len(body_bytes) <= max_body_bytes:
        return prefix + body, False

    # Truncate body to fit, leaving room for ellipsis
    suffix_bytes = TRUNCATION_SUFFIX.encode("utf-8")
    allowed_bytes = max_body_bytes - len(suffix_bytes)

    truncated_body_bytes = b""
    for ch in body:
        ch_bytes = ch.encode("utf-8")
        if len(truncated_body_bytes) + len(ch_bytes) > allowed_bytes:
            break
        truncated_body_bytes += ch_bytes

    truncated_body = truncated_body_bytes.decode("utf-8", errors="ignore")
    return prefix + truncated_body + TRUNCATION_SUFFIX, True


def format_mesh_to_signal(sender_name, message_text):
    return f"[{sender_name}] {message_text}"


def format_bridge_message(text):
    return f"[{BRIDGE_PREFIX}] {text}"

def build_status_message():
    relay_state = "ON" if RELAY_ENABLED else "OFF"
    return format_bridge_message(
        f"Message relaying is {relay_state}. MODE{RELAY_MODE} is active."
    )

# -------------------------
# Signal RPC helpers
# -------------------------

_rpc_id = 0

def rpc_call(method, params):
    global _rpc_id
    _rpc_id += 1
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": _rpc_id,
    }

    try:
        r = requests.post(SIGNAL_RPC_URL, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning(f"Signal RPC error: {e}")
        return {}


def send_to_signal(message, sender_label=None, log_relay=True):
    try:
        rpc_call("send", {
            "groupId": SIGNAL_GROUP_ID,
            "message": message
        })
        if log_relay:
            log.info(f"Relayed Mesh → Signal ({sender_label})")
    except Exception as e:
        log.error("Signal send failed: %s", e)

# -------------------------
# Mesh helpers
# -------------------------
        
def send_to_mesh(iface, message, sender_label=None, log_relay=False):
    MESH_TX_QUEUE.put((message, sender_label, log_relay))

def get_node_display_name(node_id, interface):
    try:
        if node_id and node_id in interface.nodes:
            user = interface.nodes[node_id].get("user", {})
            if user.get("shortName"):
                return user["shortName"].strip()
            if user.get("longName"):
                return user["longName"].split()[0][:8]
    except Exception:
        pass

    if node_id and node_id.startswith("!") and len(node_id) > 5:
        return node_id[1:][-4:].upper()

    return "????"

# -------------------------
# Mesh command handling
# -------------------------

COMMAND_REGISTRY = {}

def mesh_command(name):
    def decorator(func):
        COMMAND_REGISTRY[name] = func
        return func
    return decorator

# ------------------- COMMANDS -------------------

#!Test command
@mesh_command("test")
def test(args, iface, ctx):
    hops = ctx.get("hops")

    if hops is None:
        hop_text = "? hops"
    elif hops == 0:
        hop_text = "0 hops"
    elif hops == 1:
        hop_text = "1 hop"
    else:
        hop_text = f"{hops} hops"

    send_to_mesh(
        iface,
        format_bridge_message(f"{hop_text}")
    )

test.description = "!test — Verify bridge is online, hop distance to bridge."

#!On command
@mesh_command("on")
def relay_on(args, iface, ctx):
    global RELAY_ENABLED

    if RELAY_ENABLED:
        send_to_mesh(
            iface,
            format_bridge_message("Relay already enabled. Use !off to disable.")
        )
        return

    RELAY_ENABLED = True
    log.info(f"Relay ENABLED ({ctx['label']})")
    send_to_mesh(
        iface,
        format_bridge_message("Relay enabled. Use !off to disable.")
    )
    
    send_to_signal(
        format_bridge_message(f"Relay ENABLED by {ctx['label']}."),
        log_relay=False
    )


relay_on.description = "!on — Enable message relaying."

#!Off command
@mesh_command("off")
def relay_off(args, iface, ctx):
    global RELAY_ENABLED

    if not RELAY_ENABLED:
        send_to_mesh(
            iface,
            format_bridge_message("Relay already disabled. Use !on to enable.")
        )
        return

    RELAY_ENABLED = False
    log.info(f"Relay DISABLED ({ctx['label']})")
    send_to_mesh(
        iface,
        format_bridge_message("Relay disabled. Use !on to enable.")
    )
    
    send_to_signal(
        format_bridge_message(f"Relay DISABLED by {ctx['label']}."),
        log_relay=False
    )

relay_off.description = "!off — Disable all message relaying."

#!Mode command
@mesh_command("mode")
def mode(args, iface, ctx):
    send_to_mesh(
        iface,
        format_bridge_message("Use !mode1, !mode2, !mode3, or !help mode1/2/3")
    )

mode.description = "!mode — Set relay modes using !mode[1,2,3]."

#!Mode1 command
@mesh_command("mode1")
def mode1(args, iface, ctx):
    global RELAY_MODE
    RELAY_MODE = 1
    log.info(f"MODE1 enabled ({ctx['label']})")
    send_to_mesh(
        iface,
        format_bridge_message("MODE1 enabled. Relay all messages between Mesh and Signal. Default.")
    )
    
    send_to_signal(
        format_bridge_message(
            f"MODE1 enabled by {ctx['label']}. Relay all messages between Mesh and Signal."
        ),
        log_relay=False
    )

mode1.description = "!mode1 — Relay all messages between Mesh and Signal. Default."

#!Mode2 command
@mesh_command("mode2")
def mode2(args, iface, ctx):
    global RELAY_MODE
    RELAY_MODE = 2
    log.info(f"MODE2 enabled ({ctx['label']})")
    send_to_mesh(
        iface,
        format_bridge_message(
            "MODE2 enabled. Relay all Signal → Mesh. Mesh → Signal REQUIRES !relay [message]."
        )
    )
    
    send_to_signal(
        format_bridge_message(
            f"MODE2 enabled by {ctx['label']}. Relay all Signal → Mesh. Mesh → Signal REQUIRES !relay [message]."
        ),
        log_relay=False
    )

mode2.description = "!mode2 — Relay all Signal → Mesh. Mesh → Signal REQUIRES !relay [message]."

#!Mode3 command
@mesh_command("mode3")
def mode3(args, iface, ctx):
    global RELAY_MODE
    RELAY_MODE = 3
    log.info(f"MODE3 enabled ({ctx['label']})")
    send_to_mesh(
        iface,
        format_bridge_message(
            "MODE3 enabled. Mesh → Signal ONLY via !relay [message]. Signal → Mesh relay DISABLED."
        )
    )
    
    send_to_signal(
        format_bridge_message(
            f"MODE3 enabled by {ctx['label']}. Mesh → Signal ONLY via !relay [message]. Signal → Mesh relay DISABLED."
        ),
        log_relay=False
    )

mode3.description = "!mode3 — Mesh → Signal ONLY via !relay [message]. Signal → Mesh relay DISABLED."

#!Status command
@mesh_command("status")
def status(args, iface, ctx):
    send_to_mesh(iface, build_status_message())

status.description = "!status — Show relay state and active mode."

#!Relay command
@mesh_command("relay")
def relay(args, iface, ctx):
    if not args:
        send_to_mesh(iface, format_bridge_message("Usage: !relay <message>"))
        return

    message = " ".join(args)
    sender = ctx["label"]

    if RELAY_MODE == 1:
        send_to_mesh(
            iface,
            format_bridge_message("MODE1 enabled. !relay not needed in this mode.")
        )

    if RELAY_MODE in (1, 2, 3):
        send_to_signal(
            format_mesh_to_signal(sender, message),
            sender_label=sender
        )

relay.description = "!relay <message> — Explicitly relay a message using the bridge. Modes[2,3] only."

#!Help command
@mesh_command("help")
def help(args, iface, ctx):
    if args:
        cmd = args[0].lower()
        
        handler = COMMAND_REGISTRY.get(cmd)
        if not handler:
            send_to_mesh(iface, format_bridge_message("Unknown command. Try !help."))
            log.info(f"Mesh !help for unknown command: !{cmd} ({ctx['label']})")
            return
        log.info(f"Mesh !help for command: !{cmd} ({ctx['label']})")
        desc = getattr(handler, "description", "No help available.")
        send_to_mesh(iface, format_bridge_message(desc))
        return

    #log.info(f"!help command requested ({ctx['label']})")
    send_to_mesh(
        iface,
        format_bridge_message(
            "Try !test, !on/!off, !mode, !status, !relay, or !help [command]"
        )
    )

help.description = "!help [command] — Show help for a command."

# -------------------------
# Command dispatcher
# -------------------------

def handle_mesh_command(text, iface, ctx):
    if not text.startswith(COMMAND_PREFIX):
        return False

    parts = text[len(COMMAND_PREFIX):].strip().split()
    if not parts:
        send_to_mesh(iface, format_bridge_message("Empty command. Try !help."))
        return True

    command = parts[0].lower()
    args = parts[1:]

    handler = COMMAND_REGISTRY.get(command)
    if not handler:
        send_to_mesh(iface, format_bridge_message("Unknown command. Try !help."))
        log.info(f"Unknown command: !{command} ({ctx['label']})")
        return True

    log.info(f"Executing mesh command: !{command} ({ctx['label']})")
    handler(args, iface, ctx)
    return True

# -------------------------
# Mesh receive handler
# -------------------------

def on_mesh_message(packet, interface):
    try:
        decoded = packet.get("decoded")
        if not decoded:
            return

        pkt_channel = packet.get("channel")
        if MESH_CHANNEL_INDEX != 0:
            if pkt_channel != MESH_CHANNEL_INDEX:
                return
        else:
            if pkt_channel is not None and pkt_channel != 0:
                return

        text = decoded.get("text")
        if not text or text.startswith("["):
            return

        node_id = packet.get("fromId")
        if not node_id:
            from_num = packet.get("from")
            if from_num is not None:
                node_id = f"!{from_num:08x}"
            else:
                return

        label = get_node_display_name(node_id, interface)
        
        #Get hop count
        hop_start = packet.get("hopStart")
        hop_limit = packet.get("hopLimit")
        
        hops = None
        if hop_start is not None and hop_limit is not None:
            hops = hop_start - hop_limit
        
        ctx = {
            "node_id": node_id,
            "label": label,
            "hops": hops,
        }


        if handle_mesh_command(text, interface, ctx):
            return

        if not RELAY_ENABLED:
            return
        
        # MODE1: allow
        # MODE2/3: block normal messages (must use !relay)
        if RELAY_MODE != 1:
            return

        send_to_signal(
            format_mesh_to_signal(label, text),
            sender_label=label
        )

    except Exception as e:
        log.error("Error handling mesh message: %s", e, exc_info=True)
        log.error("RAW PACKET: %s", packet)

# -------------------------
# Signal polling
# -------------------------

def handle_signal_results(results, iface):
    for item in results:
        env = item.get("envelope", {})

        # -------- DROP OLD SIGNAL MESSAGES --------
        msg_time = env.get("timestamp", 0)
        if msg_time < BRIDGE_START_TIME:
            continue
        # -----------------------------------------

        msg = None
        group = None

        if "dataMessage" in env:
            dm = env["dataMessage"]
            msg = dm.get("message")
            group = dm.get("groupInfo", {}).get("groupId")
        elif "syncMessage" in env and "sentMessage" in env["syncMessage"]:
            sm = env["syncMessage"]["sentMessage"]
            msg = sm.get("message")
            group = sm.get("groupInfo", {}).get("groupId")

        if not msg or group != SIGNAL_GROUP_ID or msg.startswith("["):
            continue

        # -------- SIGNAL COMMAND: !status --------
        if msg.strip().lower() == "!status":
            sender = format_signal_sender_name(env.get("sourceName"), env.get("source"))
            status_msg = build_status_message()

            rpc_call("send", {
                "groupId": SIGNAL_GROUP_ID,
                "message": status_msg
            })

            log.info(f"Executing Signal command: !status ({sender})")
            continue
        # -----------------------------------------

        if not RELAY_ENABLED:
            continue

        if MESH_CHANNEL_INDEX == 0:
            send_to_signal(PRIMARY_BLOCK_MESSAGE, log_relay=False)
            continue

        sender = format_signal_sender_name(env.get("sourceName"), env.get("source"))

        # MODE3 only allows Signal → Mesh via explicit !relay
        if RELAY_MODE == 3:
            continue
        
        final_message, was_truncated = truncate_signal_to_mesh_message(sender, msg)
        
        send_to_mesh(
            iface,
            final_message,
            sender_label=sender,
            log_relay=True
        )
        
        if was_truncated:
            send_to_signal(
                format_bridge_message(
                    "Message relayed to mesh, but truncated to fit Meshtastic 200-byte limit."
                ),
                log_relay=False
            )


def poll_signal_loop(iface):
    while True:
        try:
            resp = rpc_call("receive", {})
            if resp and resp.get("result"):
                handle_signal_results(resp["result"], iface)
        except Exception as e:
            log.warning(f"Signal poll error: {e}")
        time.sleep(POLL_INTERVAL)

# -------------------------
# Main Startup
# -------------------------

def main():
    log.info("======================================")
    log.info(" Meshtastic ↔ Signal Bridge")
    log.info("======================================")
    log.info("Device: %s", MESH_DEVICE)
    log.info("Mesh channel index: %s", MESH_CHANNEL_INDEX)
    log.info("Signal group: %s", SIGNAL_GROUP_ID)
    log.info("Poll interval: %s sec", POLL_INTERVAL)
    log.info("Node DB warmup: %s sec", NODE_DB_WARMUP)
    log.info("Log level: %s", LOG_LEVEL)
    log.info("Signal short names: %s", SIGNAL_SHORT_NAMES)
    log.info("")
    log.info("Connecting to Meshtastic on %s...", MESH_DEVICE)
    
    iface = SerialInterface(devPath=MESH_DEVICE)
    log.info("Meshtastic connected")

    log.info("Waiting %s seconds for node database to populate...", NODE_DB_WARMUP)
    time.sleep(NODE_DB_WARMUP)
    
    #Mesh TX queue worker
    threading.Thread(target=mesh_tx_worker, args=(iface,), daemon=True).start()

    node_count = len(iface.nodes) if hasattr(iface, 'nodes') else 0
    log.info(f"Node database ready ({node_count} nodes known)")
    

    log.info("")
    if MESH_CHANNEL_INDEX == 0:
        log.warning("Signal → Mesh relay is DISABLED while MESH_CHANNEL_INDEX=0")

    log.info("Mesh commands: !help, !test, !on/!off, !mode[1,2,3], !status, !relay")
    log.info("Signal commands: !status")
    log.info("")
    log.info("======================================")
    log.info("Bridge active - relaying messages")
    log.info("======================================")

    pub.subscribe(on_mesh_message, "meshtastic.receive")
    poll_signal_loop(iface)


if __name__ == "__main__":
    main()
