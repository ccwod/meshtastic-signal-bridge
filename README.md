# meshtastic-signal-bridge

**A Dockerized bridge to enable communication between Meshtastic nodes and Signal.**

---
## Contents
- [**Introduction**](#introduction)

- [**How It Works**](#how-it-works)

- [**Important Requirements**](#important-requirements)

- [**Getting Started**](#getting-started)

- [**Installation**](#installation)

- [**Post-installation**](#post-installation)

- [**Environment Variables**](#environment-variables)

- [**Commands**](#commands)

- [**Use Case**](#use-case)

- [**Caveats and Considerations**](#%EF%B8%8F-caveats-and-considerations-%EF%B8%8F)

- [**FAQs**](#faqs)

---

## Introduction

**meshtastic-signal-bridge** is a headless bridge that relays messages between Meshtastic nodes and a Signal group chat, enabling Meshtastic users to communicate with connected Signal users. The purpose is to facilitate communication between people when cellular/wireless networks are unreliable or disrupted, especially during civil unrest. It also enables offline, “Airplane-mode” communication (except BLE) for privacy conscious individuals. 


This project exists to:

- Enable backup communication in times of urgency
- Work with existing community mesh networks and Signal communities
- Be easy enough to run that any ametuer Meshtastic user can get started quickly

[Use case explained below](#use-case)

**🚨 WARNING 🚨: meshtastic-signal-bridge is NOT end-to-end encrypted. Running the bridge will introduce potential vulnerability in the secure communication chain. Run at your own risk.** [Learn more](#-security-and-trust-model)

---

## How It Works

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

[See example convos below](#-relayed-messages-appear-to-come-through-as-single-users)

---

## Important Requirements

This project assumes that:

- You have a basic understanding of Meshtastic, node configuration, and node placement 
- You already have access to a **city-wide or well-covered Meshtastic mesh** (check out [local Meshtastic groups](https://meshtastic.org/docs/community/local-groups))
- You have Docker Compose (recommended) or Docker running on a **Linux host**, such as:
  - NAS (e.g. Unraid)
  - Home server
  - Raspberry Pi
  - Always-on Linux computer
- You own a Meshtastic node (e.g. **SenseCap T1000-E**, Heltec V3, T-Beam, RAK WisBlock) that is connected **via USB** to the host - must be capable of serial connection
- The bridge node is well connected to the wider mesh (Likely requires an accompanying home base node for solid rx/tx. Ask your local mesh community.)  
- Docker Desktop on macOS and Windows does **not** support USB passthrough and is not supported

---

## Getting Started

#### Prior to building the container for the first time, complete the following:
1. Configure a secondary Meshtastic channel on the bridge node that will be shared with other nodes (same channel, name, and key). Mesh devices that will interact with the bridge must be configured to the same secondary channel slot. ⚠️ IMPORTANT ⚠️ Strongly recommend setting a key on your channel. If unset, the broader, public mesh will able to read all message content. Very bad!
2. Plug your Meshtastic node into the host using USB and ensure it's powered on.
3. Create a Signal group in the app. This is the group that will be used to interface with the bridge.

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
5. Open the logs to start the onboarding process, explained below under [Post-installation](#post-installation).


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
5. Open the logs to start the onboarding process, explained below under [Post-installation](#post-installation).

---

### Unraid

Community Apps version coming soon.

In the mean time, you can use the Docker Compose plugin on Unraid and follow the Docker Compose installation instructions above and it will work.

Manually create the project directory ahead of time under `/appdata`, (e.g. `/mnt/user/appdata/meshtastic-signal-bridge`), and when creating the stack in Docker Compose, ensure you point to the directory in the `Advanced > Stack Directory` settings when creating the stack.

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

#### `!on`/`!off` Commands
The `!on`/`!off` commands act as a global switch to enable or disable all message relay functionality, taking precedence over modes. This can be useful if you have meshtastic-signal-bridge always running in the background set to `!off` because you don't want to pollute mesh channels / Signal groups with message content from the other. When a user is in a situation where the bridge is immediately necessary to use, then they can use `!on` to turn it back on and resume bridge communications. `!on` is default.

#### `!mode` Commands
There are 3 modes the bridge can be set to which change the functionality of which messages are relayed using the bridge. The modes are designed to accommodate various communication scenarios that mesh users may be in.

 - `!mode1`: Acts as a full 2 way communication layer between the mesh channel and Signal group. Default.

 - `!mode2`: Useful if mesh users want to monitor the conversation of the broader Signal group, and are also locally coordinating messages on the mesh that they don’t want to bleed into the Signal group. Mesh users use `!relay` to send pertinent messages back to the Signal group. 

 - `!mode3`: Useful to completely minimize communications between the mesh channel and Signal group, except when communication is necessary from mesh users' side. Messages are **NOT** relayed from Signal to mesh so as to keep the mesh chatter down, and mesh users are still required to use `!relay` to send a message to Signal.

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
**🚨CAUTION🚨WARNING🚨WEEWOO🚨WEEWOO🚨THIS APP WAS MADE WITH AI🚨IF YOU DO NOT LIKE THAT PLEASE MOVE ON🚨THIS APP WAS CREATED FOR ME TO SEE IF IT COULD BE DONE🚨I WILL NOT CHANGE ANYTHING🚨I WILL NOT ADD ANYTHING🚨I MAY EVEN REMOVE SOME THINGS🚨**

However, I put a great deal of human care, consideration, review, and testing into the app. It's not perfect, but I had a strong design vision in mind when creating it.

---

### 🔴 Security and trust model

This bridge is a **trusted gateway**.

While it does not inherently log or store message content, it uses:

- [`signal-cli`](https://github.com/AsamK/signal-cli)
- [`Meshtastic Python API`](https://github.com/meshtastic/python)

Both could be modified by a bridge operator to inspect message content coming and going from either platform. 

Additionally, rouge interception and inspection of a mesh node device could potentially allow a bad actor to divulge the contents of sent/received mesh messages and also any relayed Signal messages to the mesh device.

**meshtastic-signal-bridge is NOT end-to-end encrypted. Running the bridge will introduce potential vulnerability in the secure communication chain. Run at your own risk.**

**Only run or use this bridge with people you know and trust.**

---

### 🔴 Only tested on a limited hardware configuration

- Built and tested using Docker Compose on **Unraid**
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

## FAQs

### I'm having trouble starting the bridge. What's wrong?
Have you check the logs? Have you connected your Signal account using the QR code? Have you provided a valid .env file with the default variables? Have you filled out the env variables, including MESH_DEVICE and SIGNAL_GROUP_ID?

### Are messages end-to-end secure between Meshtastic and Signal?
No, the platforms have no way to “talk” to each other. The bridge is a trusted gateway. No message content is currently exposed to the bridge, however, the bridge could be modified by somebody to read message content from each platform. [Learn more](#-security-and-trust-model)

### The bridge is running and *was* working, but now I’m having issues getting mesh messages sent out to Signal, and they don’t appear in the logs. What happened?
Have you changed the on/off or mode settings using `!off`? On/off always takes precedence over any mode, it’s a universal on/off switch for the bridge functionality. Use `!status` to determine the current mode and on/off status.

### Can I DM an individual person on Signal?
No, meshtastic-signal-bridge is currently only configured to interface with a singular Signal group. If you want to communicate with one other person, add them to a group with you and use that.

### Are multiple Signal groups supported?
Not at this time.

### Can I run multiple bridges at once?
I don't see why not. You'd need a separate container for each, and also a USB-connected mesh node for each bridge container running.

### Is it possible to associate individual Signal accounts with each mesh user so that Mesh messages come back to Signal as the “user” who is sending them?
No, this would require spinning up a separate signal-cli instance for each mesh user. Not possible at this time.

### Do I need to use the Meshtastic phone app? Can I instead use a node that has built in messaging capabilities?
While many users use the phone app to communicate by connecting to their node over BLE, it is not required to use the bridge. Theoretically, any node with messaging capabilities should work fine.

### Meshtastic has a 200 byte limit. What happens if a Signal user sends a message with content over 200 bytes?
If the bridge is enabled (`!on`, and only `!mode1` or `!mode2`) and a Signal user sends a message over 200 bytes, the message is truncated to 200 bytes before it is forwarded to the mesh. In this case, an ellipses '...' is included at the end of the message to the mesh, and also, Signal will be notified that the message was truncated. The 200 byte limit accounts for the [SIGNAL NAME] message prefix that is included on relayed Signal to mesh messages. Standard UTF-8 characters are 1 byte each, however, special characters can be more than 1 byte each, such as an emoji 📱 (4 bytes).

### The bridge is working, but I'm not getting Signal notifications on my phone for messages sent from the mesh. What gives?
If you created the bridge and linked the bridge Signal account to the same Signal account that you use on your mobile phone, you will run in to this issue. The problem is that Signal does not notify you for messages sent to/from yourself, which is technically what's happening when they come in through the bridge using signal-cli. If you want to properly get notifications on your phone, configure the bridge to run with a secondary Signal account instead. [Learn more](#-link-the-bridge-with-a-secondary-signal-account-if-possible)

### I got the error `Signal RPC error: HTTPConnectionPool(host='localhost', port=8080): Read timed out. (read timeout=60)`. What does it mean?
I don't know, I think it's some kind of errant Signal timeout that is due to Signal service disruptions and not due to the bridge. Signal messages will likely drop while it happens. Usually only happens every now and then.

### How do I reset my Signal authentication with the bridge?
Unlink the bridge from "Linked device" in your Signal account, and delete the entire `signal-data` project directory and restart the container. This will restart the authentication process and prompt you with a new linking QR code. 

---

## Contributing

PRs welcome. Improvements welcome. Experiments welcome. If you test this app, please let me know if it worked out for you.
