# meshtastic-signal-bridge

**A Dockerized bridge to enable communication between Meshtastic nodes and Signal.**

---

## Introduction

**meshtastic-signal-bridge** is a headless bridge that relays messages between Meshtastic nodes and a Signal group chat, enabling Meshtastic users to communicate with connected Signal users. The purpose is to facilitate communication between people when cellular/wireless networks are unreliable or disrupted, especially during civil unrest. It also enables offline, “Airplane-mode” communication (except BLE) for privacy conscious individuals. 


This project exists to:

- Enable backup communication in times of urgency
- Work with existing community mesh networks and Signal communities
- Be easy enough to run that any ametuer Meshtastic user can get started quickly

[Use case explained below](https://github.com/ccwod/meshtastic-signal-bridge?tab=readme-ov-file#use-case)

---

## How it works

A dedicated Meshtastic node is connected via USB to a host running the container.  
That node acts as a gateway between:

```
Meshtastic channel  ⇄  Bridge node  ⇄  Signal group
```

**Multiple mesh users** in a private mesh channel can communicate with **multiple Signal users** in a private Signal group. Messages are automatically relayed back and forth between platforms.

Messages on each side are represented as a **single virtual user** and are prefixed with the original sender identity, per platform:

```
[A123] Hello from mesh
[Joe] Hello from Signal
```

[See example convos below](https://github.com/ccwod/meshtastic-signal-bridge?tab=readme-ov-file#-relayed-messages-appear-to-come-through-as-single-users)

---

## Important Requirements

This project assumes that:

- You have a basic understanding of Meshtastic, node configuration, and node placement 
- You already have access to a **city-wide or well-covered Meshtastic mesh** (check out [local Meshtastic groups](https://meshtastic.org/docs/community/local-groups))
- You have Docker or Docker Compose running on a Linux host, such as:
  - NAS (e.g. Unraid)
  - Home server
  - Raspberry Pi
  - Always-on Linux computer
- You own a Meshtastic node (e.g. **SenseCap T1000-E**, Heltec V3, T-Beam, RAK WisBlock) that is connected via USB to the host - must be capable of serial connection
- The bridge node is well connected to the wider mesh (Likely requires an accompanying home base node for solid rx/tx. Ask your local mesh community.)

---

## Getting Started

#### Prior to building the container for the first time, complete the following:
1. Configure a secondary Meshtastic channel on the bridge node that will be shared with other nodes (channel, name, and key). Mesh devices that will interact with the bridge must be configured to the same secondary channel slot.
2. Plug your Meshtastic node into the host using USB and ensure it's powered on.
3. Create a Signal group and add at least 1 additional user to start. This is the group that will be used to interface with the bridge.


#### On first startup the container will:

1. Prompt you to link your Signal account using a QR code
2. Help you find your Signal group ID
3. Help you detect your Meshtastic USB device if it is plugged in, powered on, and accessible by Docker via USB

The logs will guide you through the initial setup.

#### After the first run:
1. Enter the environment variables for **SIGNAL_GROUP_ID** and **MESH_DEVICE** in .env variable section.
2. Rebuild the container/compose down and up to restart the container with your new variables applied.
3. If the container is configured correctly, you will see a startup sequence begin in the logs. Once the sequence reads "Bridge active - relaying messages", then the bridge is fully operational.

---

## Installation

### Docker Compose (recommended)
1. Create a project directory: `/meshtastic-signal-bridge`
2. Create an `.env` file in the root directory with the following contents (it's okay if you don't know `SIGNAL_GROUP_ID` or `MESH_DEVICE` yet, the container will help you find them on first startup):
```
# Required for Signal - GroupIDs listed on startup after Signal auth
SIGNAL_GROUP_ID=

# Required for Meshtastic - MESH_DEVICE USB path listed on startup
MESH_DEVICE=
MESH_CHANNEL_INDEX=1

# Optional tuning
SIGNAL_SHORT_NAMES=TRUE
SIGNAL_POLL_INTERVAL=2
NODE_DB_WARMUP=10
TZ=America/Chicago
LOG_LEVEL=INFO
```
3. Create a `.docker-compose.yml` file in the root directory with the following contents:

```
services:
  meshtastic-signal-bridge:
    image: ghcr.io/ccwod/meshtastic-signal-bridge:latest
    container_name: meshtastic-signal-bridge
    restart: unless-stopped
    privileged: true
    env_file:
      - .env
    environment:
      - MESH_DEVICE
      - MESH_CHANNEL_INDEX
      - SIGNAL_GROUP_ID
      - SIGNAL_POLL_INTERVAL
      - LOG_LEVEL
      - SIGNAL_SHORT_NAMES
      - TZ
      - NODE_DB_WARMUP
    volumes:
      - ./signal-data:/root/.local/share/signal-cli
    devices:
      - ${MESH_DEVICE}:${MESH_DEVICE}
```
4. "Compose up" the container to start it for the first time.
5. Open the logs to start the onboarding process, explained below under [Post-installation](https://github.com/ccwod/meshtastic-signal-bridge?tab=readme-ov-file#post-installation).


---

### Docker

1. Create a project directory: `/meshtastic-signal-bridge`
2. Create an `.env` file in the root directory with the following contents (it's okay if you don't know `SIGNAL_GROUP_ID` yet, the container will help you find it on first startup):
```
# Required for Signal - GroupIDs listed on startup after Signal auth
SIGNAL_GROUP_ID=

# Required for Meshtastic - MESH_DEVICE USB path listed on startup
MESH_DEVICE=
MESH_CHANNEL_INDEX=1

# Optional tuning
SIGNAL_SHORT_NAMES=TRUE
SIGNAL_POLL_INTERVAL=2
NODE_DB_WARMUP=10
TZ=America/Chicago
LOG_LEVEL=INFO
```
3. Find your USB device path that the mesh node is mapped to, such as `/dev/ttyACM0` or `/dev/ttyUSB1`. Use that in place of `[DEVICE PATH]:[DEVICE PATH]` below.
4. Run the initial setup:
```
docker run --rm -it \
  --name meshtastic-signal-bridge \
  --privileged \
  --env-file .env \
  -v $(pwd)/signal-data:/root/.local/share/signal-cli \
  --device [DEVICE PATH]:[DEVICE PATH] \
  ghcr.io/ccwod/meshtastic-signal-bridge:latest
```
5. Open the logs to start the onboarding process, explained below under [Post-installation](https://github.com/ccwod/meshtastic-signal-bridge?tab=readme-ov-file#post-installation).

---

### Unraid

Coming soon.

---

## Post-installation

#### On first startup the container will:

1. Prompt you to link your Signal account using a QR code.
2. Help you find your Signal group ID.
3. Help you detect your Meshtastic USB device if it is plugged in, powered on, and accessible by Docker via USB (Docker Compose only).

The logs will guide you through the initial setup.

#### After the first run:
1. Enter the environment variables for **SIGNAL_GROUP_ID** and **MESH_DEVICE** in .env variable section.
2. Rebuild the container/compose down and up to restart the container with your new variables applied.
3. If the container is configured correctly, you will see a startup sequence begin in the logs. Once the sequence reads "Bridge active - relaying messages", then the bridge is fully operational.

---

## Environment Variables

See `.env.example`

| Variable | Purpose | Default
|---|---|---|
| `SIGNAL_GROUP_ID` | ID of the target Signal group to communicate with, provided during startup after Signal account auth | `NONE` |
| `MESH_DEVICE` | USB path of the connected Meshtastic device. Listed on startup, typically something like `/dev/ttyACM*` or `/dev/ttyUSB*` | `NONE` |
| `MESH_CHANNEL_INDEX` | Channel index # for Meshtastic device to communicate on (0=PRIMARY), (1=SECOND), (2=THIRD), etc... 0 not allowed | `1` |
| `SIGNAL_SHORT_NAMES` | Signal display name based on Signal profile name. `TRUE`=first string of name, like `[Joe]`. `FALSE`=full Signal profile name, like `[Joe J Lastname]`.  | `TRUE` |
| `SIGNAL_POLL_INTERVAL` | How often signal-cli is polled for new received Signal messages, seconds. Recommend do not change. | `2` |
| `NODE_DB_WARMUP` | How many seconds to wait on for Meshtastic node list to populate on bridge startup, seconds. Recommend do not change. | `10` |
| `TZ` | Timezone used for logging. Common US options: `America/New_York`, `America/Chicago`, `America/Denver`, `America/Los_Angeles`.  | `America/Chicago` |
| `LOG_LEVEL` | Log level | `INFO` |

---

## Commands

### Mesh Commands

Commands can be initiated by all mesh users using the format **![command]**, or **!help [command]**. The bridge will respond back to the mesh channel for each given command, but nothing command-related will be relayed to Signal.

| Command | Purpose |
|---|---|
| `!test` | Verify the bridge is online by sending the hop distance from user to bridge |
| `!help` | Show command help and command list |
| `!help [command]` | Get help with a specific command |
| `!on` | Enable full message relay functionality, according to mode. Default. |
| `!off` | Disable all message relay functionality |
| `!mode` | Shows the mode options, `!Mode[1,2,3]` |
| `!mode1` | Automatically relay all messages between Mesh and Signal. Default. |
| `!mode2` | Relay all Signal → Mesh. Mesh → Signal relay **REQUIRES** `!relay [message]` |
| `!mode3` | Mesh → Signal **ONLY** via `!relay [message]`. Signal → Mesh relay **DISABLED**. |
| `!status` | Show relay state (`on` or `off`) and mode |
| `!relay` | Only used for Modes[2,3]. Explicitly relays messages from Mesh to Signal, otherwise they are not automatically relayed in those modes. |

### Signal Command

Signal users have access to the **!status** command to check the current configuration of meshtastic-signal-bridge, set by mesh users. This also allows Signal users to ensure the bridge is operational. 

| Command | Purpose |
|---|---|
| `!status` | Show relay state (on or off) and mode |

---

## Use Case

**meshtastic-signal-bridge** is intended to run as a complement to a primary Signal group in the form of a private, backup communication method between trusted individuals. In practice, this is how it might work:
1. A group of known people regularly communicate and coordinate via Signal for covert operations.
2. A subset (or all) of those people have access to portable Meshtastic nodes.
3. meshtastic-signal-bridge is running continuously, deployed by a trusted member of the group in a city with an established mesh. 
4. People who may find themselves in scenarios where communication could be disrupted would carry Meshtastic nodes with them, such as at a protest, demonstration, or action. In the unlikely event that communication is disrupted for people carrying Meshtastic nodes, they could use their node as a backup communication method to facilitate communication with the broader Signal group, alerting them of their current status, location, etc.
5. Alternatively, the bridge may be utilized for privacy-focused users who wish to temporarily communicate with others while using their phone in Airplane Mode (except BLE). This could be due to suspicion of tracking via methods such as [obtaining mobile location data](https://www.eff.org/deeplinks/2022/06/how-federal-government-buys-our-cell-phone-location-data) or using [IMSI catchers](https://www.aclu.org/news/privacy-technology/surreal-stingray-secrecy-uncovering-the-fbis-surveillance-tech-secrecy-agreements) (e.g. Stingray devices) to track users.

---

## ⚠️ Caveats and Considerations ⚠️

### 🔴 This app is mostly vibecoded!!!
**🚨CAUTION🚨WARNING🚨WEEWOO🚨WEEWOO🚨THIS APP WAS MADE WITH AI🚨IF YOU DO NOT LIKE THAT PLEASE MOVE ON🚨THIS APP WAS CREATED FOR ME AND ME ALONE🚨I WILL NOT CHANGE ANYTHING🚨I WILL NOT ADD ANYTHING🚨I MAY EVEN REMOVE SOME THINGS🚨**

However, I put a great deal of human care, consideration, review, and testing into the app. It's not perfect, but I had a strong vision in mind when creating it.

---

### 🔴 Security and trust model

This bridge is a **trusted gateway**.

While it does not inherently log or store message content, it uses:

- [`signal-cli`](https://github.com/AsamK/signal-cli)
- [`Meshtastic Python API`](https://github.com/meshtastic/python)

Both could be modified by the operator to inspect message content coming and going from either platform.

**Only run this bridge with people you trust.**

---

### 🔴 Only tested on a limited hardware configuration

- Built and tested using Docker-Compose on **Unraid**
- Tested with **SenseCap T1000-E**
- Designed for Docker first
- May work on other configurations — try at your own risk

---

### 🔴 Meshtastic is fragile and fallible

Meshtastic is an intriguing, experimental, niche technology. It is extremely fallible. Messages can easily get lost in the mesh. Receiving messages in the mesh is easy, sending is hard. **Meshtastic should never be used for vital, emergency comms.**

---

### 🔴 Supported content types

meshtastic-signal-bridge only supports relaying basic message body content due to the fact that Meshtastic is an extremely low-bandwidth platform.

#### From Meshtastic

| Feature | Supported |
|---|---|
| Text messages | ✅ |
| Emoji reactions from Mesh | ✅ (as text) |
| Other device telemetry | ❌ |

- Messages are kept intentionally short for reliable mesh delivery.

#### From Signal

| Feature | Supported |
|---|---|
| Text messages | ✅ |
| Message reactions | ❌ |
| Replies / quotes | ❌ |
| Images / media | ❌ |
| Chat events | ❌ |

 - While replies/quotes are not supported, the main message body content will be relayed; it just won't contain the contextual replied-message content.

---

### 🔴 Link the bridge with a secondary Signal account if possible

If you use **your own Signal account** to link to the bridge, Signal **will NOT notify your phone of new messages** coming from the mesh. The scenario for this would be if you are planning to actively communicate with the Signal group on your phone, and you used the same Signal account to link to the bridge. In that case, when mesh users send messages (which are then relayed by the bridge into the Signal group), you will not receive a mobile notification from the Signal app about new messages from mesh users.

This is because Signal does not notify you for messages sent **to/from yourself**, which is technically what's happening when they come in through the bridge using signal-cli.

**Recommended setup:**
- Use or create a **secondary Signal account** (second phone / number, or use a trusted friend or partner's Signal account)
- Add the secondary account to the Signal group
- Link the secondary account to the bridge
- Keep your primary account in the group for personal mobile usage
- This way **will** alert your phone on your primary account when new messages come in from the mesh

---

### 🔴 Relayed messages appear to come through as single users

Messages on each side are represented as a **single virtual user** per platform. Messages are prefixed with a basic sender identity from the other platform.

#### Meshtastic

A USB connected bridge node is required to facilitate mesh interactions. Any messages received from Signal on the mesh side will appear to originate from the bridge node. Messages relayed from Signal will be prefixed with the `[SIGNAL NAME]` of the sending Signal user, but will appear as being sent from the bridge node. Messages between mesh users in the mesh channel group will appear normally. This is how a 2-way conversation could look from the mesh side:
```
NOD1: Hey guys

NOD2: Signal, can you hear us?

BRDG: [Joe] Coming in good

BRDG: [Tom] Yep

NOD1: Great, thanks

BRDG: [Tom] See you soon
```

#### Signal

Similarly, the bridge must be linked to a single Signal account to properly connect to the Signal group. Messages received in the Signal chat from mesh users will appear to originate from a single Signal user, prefixed with the `[NODE]` short name of the sending node. Messages between Signal users in the Signal group chat will appear normally. Conversely, this is how the same 2-way conversation would look from the Signal side:
```
Joe: [NOD1] Hey guys

Joe: [NOD2] Signal, can you hear us?

Joe: Coming in good

Tom: Yep

Joe: [NOD1] Great, thanks

Tom: See you soon
```

---

### 🔴 Do NOT use Channel Index 0 (Primary) for MESH_CHANNEL_INDEX

Channel 0 is the primary, public channel on Meshtastic by default, and thus, we don't want to spam the precious mesh network. It is possible to set Channel Index to 0 for limited testing, however, the bridge is constrained in this mode.

When `MESH_CHANNEL_INDEX=0`:

- **Mesh → Signal works**. You can test and ensure messages are being relayed to the Signal group. Suitable when you're testing the bridge but don't have an extra node or node-friend to send messages to the bridge; you can just listen to the public mesh chatter and check that it's going into Signal.
- **Signal → Mesh is blocked**, intentionally. We don't want to spam a mesh's open, public channel with the vast and numerous contents of a Signal group.
- Logs will explicitly warn you when Channel Index is set to 0.

**Recommended Setup:**

Create a **secondary channel** on all nodes:

- Same channel number
- Same channel name
- Same key (if using encryption, recommended)

[Meshtastic Docs - Channel Config Values](https://meshtastic.org/docs/configuration/radio/channels/#channel-config-values)

---


## Contributing

PRs welcome. Improvements welcome. Experiments welcome. If you test this app, please let me know if it worked out for you.

