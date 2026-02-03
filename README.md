# meshtastic-signal-bridge

**A Dockerized bridge to enable communication between Meshtastic nodes and Signal using signal-cli.**

---

## Introduction

**meshtastic-signal-bridge** is a headless bridge that relays messages between Meshtastic nodes and a Signal group chat, enabling Meshtastic users to communicate with connected Signal users. The purpose is to facilitate communication between people when cellular/wireless networks are unreliable or disrupted, especially during civil unrest. It also enables offline, “Airplane-mode” communication (except BLE) for privacy conscious individuals at large events or demonstrations. 


This project exists to:

- Enable backup communication in times of urgency
- Work with existing community mesh networks and Signal communities
- Be easy enough to run that any ametuer Meshtastic user can get started quickly

---

## How it works

A dedicated Meshtastic node is connected via USB to a host running the container.  
That node acts as a gateway between:

```
Meshtastic Mesh  ⇄  Bridge Node  ⇄  Signal Group
```

**Multiple mesh users** can communicate with **multiple Signal users** in a private Signal group.

Messages on each side are represented as a **single virtual user** and are prefixed with the original sender identity, per platform:

```
[A123] Hello from mesh
[Joe] Hello from Signal
```

---

## Important Requirements

This project assumes:

- You already have access to a **city-wide or well-covered Meshtastic mesh** (Check out [local Meshtastic groups](https://meshtastic.org/docs/community/local-groups))
- You have Docker running on something like a:
  - NAS (e.g. Unraid)
  - Home server
  - Raspberry Pi
  - Always-on computer
- You own a Meshtastic node (e.g. **SenseCap T1000-E**, Heltec V3, T-Beam, RAK WisBlock) that is connected via USB to the host
- The bridge node is well connected to the wider mesh (Likely requires a home base node. Ask your local mesh community.)

---

## Security & Trust Model

This bridge is a **trusted gateway**.

While it does not inherently log or store message content, it uses:

- `signal-cli`
- Meshtastic Python API

Both could be modified by the operator to inspect message content.

**Only run this bridge with people you trust.**

---

## Signal Caveat (Very Important)

If you use **your own Signal account** for the bridge:

> Signal will NOT notify you of messages coming from the mesh

This is because Signal does not notify you for messages sent **to/from yourself**.

### Recommended setup

- Use or create a **secondary Signal account** (second phone / number, or use a friend's)
- Add that account to the group
- Use that account for the bridge
- Keep your primary account in the group for notifications

---

## Platform Notes

- Built and tested using Docker-Compose on **Unraid**
- Tested with **SenseCap T1000-E**
- Designed for Docker first
- May work elsewhere — try at your own risk
- Feel free to fork, experiment, improve

---

## Supported Content

| Feature | Supported |
|---|---|
| Text messages | ✅ |
| Emoji reactions from Mesh | ✅ (as text) |
| Replies / quotes | ❌ |
| Images / media | ❌ |
| Signal reactions | ❌ |

Messages are kept intentionally short for reliable mesh delivery.

---

## Meshtastic Channel Recommendations

**DO NOT** use Channel 0 for normal use.

Channel 0 is primary/public and only intended for testing.

When `MESH_CHANNEL_INDEX=0`:

- Mesh → Signal works
- Signal → Mesh is intentionally blocked
- Logs will warn you

### Recommended Setup

Create a **secondary channel** on all nodes:

- Same channel number
- Same channel name
- Same key (if using encryption)

Reference:  
https://meshtastic.org/docs/configuration/radio/channels/#channel-config-values

---

## First Run Experience

On first startup the container will:

1. Prompt you to link a Signal device (QR code)
2. Help you find your Signal group ID
3. Help you detect your Meshtastic USB device
4. Refuse to start until everything is correctly configured

The logs guide you through the entire setup.

---

## Mesh Commands

| Command | Purpose |
|---|---|
| `!test` | Verify bridge is online + hop distance |
| `!help` | Show command help |
| `!help [command]` | Get help about a specific command |
| `!on` | Enable message relay |
| `!off` | Disable message relay |
| `!mode` | Shows the mode options |
| `!mode1` | Normal relay both ways |
| `!mode2` | Signal → Mesh always, Mesh → Signal only with `!relay` |
| `!mode3` | Mesh → Signal only with `!relay`, Signal → Mesh disabled |
| `!status` | Show relay state and mode |

### Signal Command

| Command | Purpose |
|---|---|
| `!status` | Always returns bridge state |

---

## Ideal Bridge Node Settings

The bridge node can be configured to any device role, but **client** or **client_mute** is likely ideal.

---

## Environment Variables

See `.env.example`

| Variable | Purpose | Default
|---|---|---|
| `SIGNAL_GROUP_ID` | ID of the target Signal group to communicate with, provided during startup after Signal account auth | `NONE` |
| `MESH_DEVICE` | USB path of the connected Meshtastic device. Listed on startup, typically something like `/dev/ttyACM*` or `/dev/ttyUSB*` | `NONE` |
| `MESH_CHANNEL_INDEX` | Channel index # for Meshtastic device to communicate on (0=PRIMARY), (1=SECOND), (2=THIRD), etc... 0 not allowed | `1` |
| `SIGNAL_SHORT_NAMES` | Signal display name based on profile name. TRUE=first string of name. FALSE=full Signal profile name. `[Joe]` vs `[Joe J Lastname]` | `TRUE` |
| `SIGNAL_POLL_INTERVAL` | How often signal-cli is polled for new received Signal messages, seconds. Recommend do not change. | `2` |
| `NODE_DB_WARMUP` | How many seconds to wait on for Meshtastic node list to populate on bridge startup, seconds. Recommend do not change. | `10` |
| `TZ` | Timezone used for logging. Common US options: `America/New_York`, `America/Chicago`, `America/Denver`, `America/Los_Angeles`.  | `America/Chicago` |
| `LOG_LEVEL` | Log level | `INFO` |


---

## Running

```bash
docker-compose up -d
docker logs -f meshtastic-signal-bridge
```

Follow the logs for setup.

---

## Contributing

PRs welcome. Improvements welcome. Experiments welcome.

---

## License

TBD
