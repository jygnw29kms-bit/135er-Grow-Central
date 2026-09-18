#!/usr/bin/env python3
"""Build a Grow-Central theme from an official Plesk theme export."""
import argparse
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET
import zipfile

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True, type=Path)
    p.add_argument("--logo", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    if a.output.resolve() == a.base.resolve():
        p.error("Output must differ from the original theme export")
    with zipfile.ZipFile(a.base) as archive:
        entries = {}
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts:
                p.error("Unsafe archive entry")
            if not item.is_dir():
                entries[item.filename] = archive.read(item)
    if "meta.xml" not in entries:
        p.error("Plesk export must contain meta.xml at the archive root")
    meta = ET.fromstring(entries["meta.xml"])
    for tag, value in {
        "name": "grow-central",
        "description": "135er Grow-Central dark, cyan and lime branding",
        "version": "1.0.0",
        "vendor": "135er Grow-Central",
    }.items():
        element = meta.find(tag)
        if element is None:
            element = ET.SubElement(meta, tag)
        element.text = value
    entries["meta.xml"] = ET.tostring(meta, encoding="utf-8", xml_declaration=True)
    entries["css/custom.css"] = (Path(__file__).parent / "css/custom.css").read_bytes()
    entries["images/grow-central-lockup.png"] = a.logo.read_bytes()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(a.output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, data in sorted(entries.items()):
            archive.writestr(path, data)
    print(f"Built {a.output}: {len(entries)} files")

if __name__ == "__main__":
    main()
