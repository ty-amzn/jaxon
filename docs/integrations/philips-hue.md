# Philips Hue

Control your Philips Hue smart lights with natural language via the local CLIP API v2. All communication stays on your LAN — no cloud required.

## What You Get

| Action | Example prompt | What it does |
|--------|---------------|--------------|
| `list_lights` | "What lights do I have?" | Lists all lights with name, state, brightness |
| `list_rooms` | "Show me my Hue rooms" | Lists rooms with grouped light IDs and states |
| `list_scenes` | "What scenes are available?" | Lists scenes grouped by room |
| `control_light` | "Set the desk lamp to 50% warm white" | Controls a single light (on/off, brightness, color, color temp) |
| `control_room` | "Turn off the bedroom" | Controls all lights in a room at once |
| `activate_scene` | "Activate the Relax scene" | Activates a preconfigured Hue scene |

Supports named colors (red, blue, green, purple, pink, orange, cyan, warm white, cool white), color temperature presets (warm/cool/neutral), mirek values (153–500), brightness (0–100%), and transition durations.

## Prerequisites

- A Philips Hue Bridge on your local network
- At least one Hue light paired with the bridge

## Setup

### 1. Find your bridge IP

Your Hue Bridge IP is shown in the Hue app under **Settings → My Hue system → (your bridge) → IP address**.

Or discover it automatically:

```bash
curl -s https://discovery.meethue.com | python3 -m json.tool
```

This returns something like:

```json
[{"id": "001788fffe123456", "internalipaddress": "192.168.1.100", "port": 443}]
```

### 2. Generate an API key

The Hue Bridge requires a one-time button press to authorize a new application.

1. **Press the link button** on top of your Hue Bridge
2. **Within 30 seconds**, run:

```bash
curl -sk -X POST "https://YOUR_BRIDGE_IP/api" \
  -H "Content-Type: application/json" \
  -d '{"devicetype": "jaxon#assistant", "generateclientkey": true}'
```

Replace `YOUR_BRIDGE_IP` with the IP from step 1. The `-k` flag is needed because the bridge uses a self-signed certificate.

A successful response looks like:

```json
[{"success": {"username": "AbCdEf0123456789...", "clientkey": "01234567-89AB-CDEF-..."}}]
```

The `username` value is your API key. Save it — you'll need it in step 3.

If you see `"link button not pressed"`, press the button again and retry within 30 seconds.

### 3. Configure the assistant

Add to your `.env`:

```bash
ASSISTANT_HUE_ENABLED=true
HUE_BRIDGE_IP=192.168.1.100
HUE_API_KEY=AbCdEf0123456789...
```

### 4. Verify

```bash
uv run assistant chat
```

Try:
- "List my Hue lights" → see all lights with names and states
- "Turn on the living room lights" → controls the room
- "Set the bedroom to 30% warm white" → brightness + color temp
- "Activate the Relax scene" → scene activation

## Typical Workflow

The assistant usually needs two steps to control your lights:

1. **List first** — "What lights/rooms/scenes do I have?" to discover resource IDs
2. **Control** — "Turn off the bedroom" or "Set the desk lamp to blue" using the discovered IDs

After the first interaction the assistant remembers your light and room names from context, so subsequent commands in the same session are direct.

## Named Colors

These color names work out of the box:

| Name | CIE xy |
|------|--------|
| red | 0.675, 0.322 |
| green | 0.409, 0.518 |
| blue | 0.167, 0.040 |
| yellow | 0.443, 0.515 |
| orange | 0.556, 0.408 |
| purple | 0.270, 0.140 |
| pink | 0.394, 0.199 |
| cyan | 0.150, 0.300 |
| warm white | 0.460, 0.411 |
| cool white | 0.323, 0.329 |
| white | 0.313, 0.329 |

For other colors, use raw CIE coordinates: `"xy:0.3,0.4"`.

## Color Temperature Presets

| Preset | Mirek | Approximate Kelvin |
|--------|------:|-------------------:|
| warm | 400 | ~2500K |
| neutral | 300 | ~3333K |
| cool | 200 | ~5000K |

Or pass a raw mirek value (153–500) directly.

## Troubleshooting

### "Hue Bridge IP and API key are not configured"
- Check that `HUE_BRIDGE_IP` and `HUE_API_KEY` are set in `.env` (no `ASSISTANT_` prefix)
- Check that `ASSISTANT_HUE_ENABLED=true`

### "Hue Bridge request failed" / connection errors
- Verify the bridge IP is correct and reachable: `ping YOUR_BRIDGE_IP`
- The bridge uses HTTPS with a self-signed certificate — the tool handles this automatically
- Make sure your machine is on the same network as the bridge

### "unauthorized" or 403 errors
- Your API key may be invalid — regenerate it by pressing the link button and running the curl command again
- Check that the `HUE_API_KEY` matches the `username` from the generation response

### Lights not responding to control commands
- Use `list_lights` or `list_rooms` first to get the correct resource IDs
- For room control, you need the **grouped_light ID** (shown by `list_rooms`), not the room ID
- Check that the light is reachable in the Hue app

### Bridge IP changed
- Hue bridges can get a new IP after a router restart
- Re-run the discovery command from step 1 to find the new IP
- Consider assigning a static IP or DHCP reservation to the bridge
