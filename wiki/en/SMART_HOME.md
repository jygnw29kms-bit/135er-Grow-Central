# Smart Home

The v0.6 architecture connects Shelly Gen2+ directly on the LAN. Tapo and FRITZ!SmartHome use an optional Home Assistant connector. Apple Home and Siri are reached through Home Assistant HomeKit Bridge. Matter is the later standards-based bridge target.

Security principle: a discovered device never becomes writable automatically. Approval, write permission, global enablement and local authentication are separate gates.
