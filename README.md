# Yandex HA Bridge

Home Assistant add-on that reads Yandex Smart Home devices through the official Yandex Smart Home API.

## Current version

**0.1.0 — read-only discovery**

The first version does not control the device. It validates OAuth access and discovers the Yandex device **YNDX-00019** from Home Assistant add-on logs.

## Security

The OAuth token is configured locally in Home Assistant. It is never stored in this repository and must never be committed to GitHub.

## Roadmap

- 0.1.0 — API authentication and YNDX-00019 discovery
- 0.2.0 — device control
- 0.3.0 — automatic Home Assistant `light` entity via MQTT Discovery
- 0.4.0 — state synchronization
- later — multiple devices and additional capabilities
