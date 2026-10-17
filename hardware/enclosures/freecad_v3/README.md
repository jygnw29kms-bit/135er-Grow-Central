# Grow-Central enclosure V3

Production CAD for Bambu Lab P2S, 0.4 mm nozzle, 0.20 mm Standard.

## Variants
- Pi4: Raspberry Pi 4 enclosure with raised two-colour Grow-Central branding.
- Node FPC: enlarged compact Node enclosure with protected 40 x 20 mm carrier for the supplied XIAO ESP32-C3 adhesive FPC antenna and coax strain relief.
- Node EXT: compact Node enclosure with reinforced 6.5 mm SMA/RP-SMA bulkhead opening and internal nut/cable clearance.
- Hub FPC: Hub enclosure with protected 40 x 20 mm carrier for the supplied adhesive FPC antenna.
- Hub EXT: Hub enclosure with reinforced 6.5 mm SMA/RP-SMA bulkhead opening.

## Branding
Branding is raised 0.90 mm and exported as a separate body so AMS can print it as a second colour. P2S projects map enclosure/lid to filament 1 (black) and branding to filament 2 (green). Branding and lid use the same 3MF transform.

## Verification
`validate_v3.py` checks FreeCAD solids, reference-hardware collisions, assembled base/lid fit, FPC clearance, SMA clearance and branding/lid overlap. `validate_p2s_v3.py` checks the final 3MF package, P2S 0.4 nozzle identity, 0.20 Standard process, P2S 256 mm build volume and dual-colour alignment.

Current validated CAD result: zero hardware/base, hardware/lid, base/lid and branding/lid volumetric collisions for all five variants. Physical fit still requires a real test print, because plastic has the annoying habit of existing in the real world.
