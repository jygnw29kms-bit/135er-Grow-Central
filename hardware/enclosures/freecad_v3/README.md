# Grow-Central enclosure V3

> **STATUS: PROTOTYP**  
> CAD, STL/STEP and P2S-3MF are geometrically validated, but a real test print and physical fit check are still required before any series/final approval.

Prototype CAD for Bambu Lab P2S, 0.4 mm nozzle, 0.20 mm Standard.

## Variants
- Pi4: Raspberry Pi 4 enclosure with raised two-colour Grow-Central branding.
- Node FPC: Node enclosure with a robust removable base-mounted carrier for the supplied 40 x 20 mm adhesive FPC antenna.
- Node EXT: compact Node enclosure with reinforced 6.5 mm SMA/RP-SMA bulkhead opening and internal nut/cable clearance.
- Hub FPC: Hub enclosure with the same robust removable base-mounted carrier for the supplied 40 x 20 mm adhesive FPC antenna.
- Hub EXT: Hub enclosure with reinforced 6.5 mm SMA/RP-SMA bulkhead opening.

## FPC antenna carrier prototype
The supplied adhesive antenna is **not attached to the lid**. The FPC versions use a separate, massive clip/slide carrier attached to the base so opening the lid does not pull on the thin coax or U.FL connector.

- Carrier adhesive face: 44 x 24 mm.
- Original antenna reference: 40 x 20 mm.
- 2 mm protective border around the adhesive antenna.
- Twin broad base rails and stout clip channels instead of thin spring tabs.
- Defined end stop with 0.25 mm lateral FDM clearance in the guide system.
- Dedicated coax pass-through and internal strain-relief bridge.
- Carrier, base, lid and XIAO reference are collision-free in the assembled CAD state.
- Separate `*_AntennaCarrier_PRINT_V3.stl/.step` is oriented flat for support-minimised printing.
- Node FPC and Hub FPC P2S projects contain the antenna carrier as the fourth printable object.

## Branding
Branding is raised 0.90 mm and exported as a separate body so AMS can print it as a second colour. P2S projects map enclosure/lid/carrier to filament 1 (black) and branding to filament 2 (green). Branding and lid use the same 3MF transform.

## Verification
`validate_v3.py` checks FreeCAD solids, reference-hardware collisions, assembled base/lid fit, FPC carrier/antenna seating, carrier/base stop contact, carrier/lid and carrier/XIAO clearance, SMA clearance and branding/lid overlap.

`validate_p2s_v3.py` checks the final 3MF package, P2S 0.4 nozzle identity, 0.20 Standard process, P2S 256 mm build volume, dual-colour alignment and the fourth antenna-carrier object in the two FPC projects.

Current CAD validation: **PASS, no failures**. The FPC bases, lids and antenna carriers are each single valid solids. Hardware/base, hardware/lid, base/lid, carrier/lid and carrier/XIAO volumetric collisions are 0.0 mm3. The antenna reference sits on the carrier surface with 2.0 mm protection on all four edges.

Bambu Studio was also used to open the updated Node FPC P2S project and reports **Bambu Lab P2S / 0.4 nozzle / 0.20mm Standard @BBL P2S** without the previous invalid-config dialog.

## Prototype renders
- `previews/GrowCentral_V3_PROTOTYP_Gesamtuebersicht.png` - overview of all five prototype variants plus FPC carrier details.
- `previews/GrowCentral_Node_FPC_V3_PROTOTYP_Antennenhalter_Detail.png` - Node FPC carrier with the 40 x 20 mm adhesive antenna highlighted.
- `previews/GrowCentral_Hub_FPC_V3_PROTOTYP_Antennenhalter_Detail.png` - Hub FPC carrier with the 40 x 20 mm adhesive antenna highlighted.
- Individual P2S plate renders are stored in `previews/` and marked **PROTOTYP**.

Physical fit still requires a real test print, because CAD is wonderfully obedient and molten plastic has opinions.
