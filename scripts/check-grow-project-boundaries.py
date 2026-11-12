#!/usr/bin/env python3
"""Prevent unrelated printer projects from entering Grow Central builds."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PRINTER_MARKERS = re.compile(r'\b(?:PRINTBENCH|OrcaSlicer|Bambu|P2S)\b|3d-Files|downloads/3d', re.I)
RUNTIME_ROOTS = {'app', 'web', 'shared', 'local', 'cloud', 'mobile', 'image-builder'}
SOURCE_SUFFIXES = {'.py', '.js', '.html', '.json', '.yml', '.yaml', '.sh'}


def violations(root, paths):
    errors = []
    for name in paths:
        path = Path(name)
        lowered = name.lower()
        # GrowCentral's own case and sensor-node enclosures belong to this
        # repository, but their CAD/print assets must not enter the Pi image.
        approved_cad = path.parts[:2] in {
            ('hardware', 'enclosures'),
            ('legacy', 'fusion-review-only'),
        }
        if path.suffix.lower() in {'.stl', '.3mf', '.scad'}:
            if approved_cad:
                continue
            errors.append(f'Unrelated printer asset/workflow: {name}')
            continue
        if any(part in lowered for part in ('printbench', 'downloads/3d', 'build-rpi4-case')):
            errors.append(f'Unrelated printer asset/workflow: {name}')
            continue
        active = path.parts[0] in RUNTIME_ROOTS or path.parts[:2] == ('.github', 'workflows')
        if active and path.suffix in SOURCE_SUFFIXES and (root / path).is_file():
            if PRINTER_MARKERS.search((root / path).read_text(encoding='utf-8')):
                errors.append(f'Printer integration in runtime/build source: {name}')
    return errors


def main():
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    errors = violations(ROOT, [name for name in tracked if name])
    for error in errors: print(error, file=sys.stderr)
    if not errors: print('Grow project boundary check passed')
    return int(bool(errors))


if __name__ == '__main__': sys.exit(main())
