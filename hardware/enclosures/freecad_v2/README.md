# Grow-Central FreeCAD V2 enclosures

Completely new enclosure construction based on imported hardware reference STEP models.

## Current models
- GrowCentral_Pi4_V2
- GrowCentral_XIAO_Node_V2
- GrowCentral_XIAO_Hub_V2

## Design method
The enclosures are built around hardware reference geometry, not by modifying the former V1 cases.

Raspberry Pi 4 reference geometry includes the board and connector stack. XIAO ESP32-C3 reference geometry uses a 22.32 x 17.78 mm model plus explicit 2.54 mm header strips with plastic carriers and pin protrusion above/below the PCB.

## Fit validation
`validate_v2.py` performs FreeCAD BRep validation and calculates the common volume between the hardware reference and each enclosure part.

Current result:
- Pi4 reference / Base: 0.0 mm3 collision
- Pi4 reference / Lid: 0.0 mm3 collision
- XIAO Node reference / Base: 0.0 mm3 collision
- XIAO Node reference / Lid: 0.0 mm3 collision
- XIAO Hub reference / Base: 0.0 mm3 collision
- XIAO Hub reference / Lid: 0.0 mm3 collision

All exported enclosure parts are valid single solids.

## Reference sources
Reference STEP files are kept locally in `references/` for CAD validation and are not intended to replace official manufacturer mechanical drawings. Raspberry Pi dimensions must continue to be checked against official Raspberry Pi mechanical data. XIAO dimensions are checked against Seeed Studio mechanical dimensions.

## Output
Editable FreeCAD, STEP and STL working outputs are generated under `models/`.
