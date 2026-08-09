# Smart-Home Architecture – 135er GrowControl v0.6

## Objective

Smart-home interoperability extends GrowControl without changing the local trust model: the Raspberry Pi remains authoritative for device inventory, command permissions and safety policy.

## Best-path design

### Native local adapters

GrowControl integrates directly only where a stable local protocol is suitable. v0.6 implements a baseline adapter for Shelly Gen2+ JSON-RPC.

### Home Assistant interoperability bridge

Home Assistant is optional and is used as a compatibility layer, not as the GrowControl master. It is the preferred path for:

- Apple Home and Siri through HomeKit Bridge;
- TP-Link Tapo;
- FRITZ!SmartHome / FRITZ!DECT;
- additional ecosystems already maintained by Home Assistant.

GrowControl uses a restricted Home Assistant REST connector with an explicit device inventory. It does not expose an arbitrary Home Assistant service proxy.

### Matter

Matter is the future standards-based ecosystem bridge. Native Matter commissioning/bridge support is deliberately postponed until local device control, authentication, audit and recovery are mature.

## Internal command flow

```text
UI / automation / bridge
          |
          v
  authentication
          |
          v
   device registry
          |
          v
 policy + capability check
          |
          v
      adapter
          |
          v
       device
          |
          v
 read-back + audit
```

## Discovery and approval

Discovery never grants control. New devices must be explicitly entered/approved and marked writable before a command can reach an adapter.

## Smart plugs

Smart plugs control real electrical loads. GrowControl therefore separates:

- discovery/read permission;
- approved inventory;
- writable permission;
- global smart-home enable switch;
- local API write authentication;
- adapter-level read-only mode.

## Apple Home / Siri

Supported v0.6 architecture:

```text
GrowControl <-> Home Assistant -> HomeKit Bridge -> Apple Home / Siri
```

This provides practical local interoperability without claiming that GrowControl itself is a certified HomeKit accessory.

## Tapo and FRITZ!

Supported v0.6 architecture:

```text
Tapo / FRITZ! -> Home Assistant maintained integration -> GrowControl HA connector
```

This avoids duplicating vendor authentication/protocol complexity inside the GrowControl core.

## Shelly

Shelly Gen2+ is the first native smart-plug adapter because the vendor documents local JSON-RPC over HTTP/WebSocket. The current adapter uses restricted local HTTP JSON-RPC and requires a literal private/link-local IP address to reduce arbitrary-host abuse.
