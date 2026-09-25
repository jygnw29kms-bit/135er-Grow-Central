"""Personal planner helpers: Brandenburg holidays and safe XLSX import.

The workbook reader intentionally uses only the Python standard library. It reads
cached cell values from the Personalplaner-Pro template and never evaluates Excel
formulas or external links.
"""

from __future__ import annotations

import calendar
import hashlib
import io
import posixpath
import re
import zipfile
from collections import Counter
from datetime import date, timedelta
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET


BRANDENBURG = "Brandenburg"
BRANDENBURG_CODE = "BB"
MAX_WORKBOOK_BYTES = 5 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 30 * 1024 * 1024
MAX_ZIP_ENTRIES = 2_000
MAX_EMPLOYEES = 200

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


class WorkbookImportError(ValueError):
    """Raised when an uploaded workbook is unsafe or does not match the template."""


def _easter_sunday(year: int) -> date:
    """Gregorian Easter Sunday using the Meeus/Jones/Butcher algorithm."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def brandenburg_holidays(year: int) -> list[dict[str, str]]:
    """Return all statutory holidays for the State of Brandenburg."""
    if year < 1900 or year > 2200:
        raise ValueError("Ungültiges Feiertagsjahr")
    easter = _easter_sunday(year)
    items = [
        (date(year, 1, 1), "Neujahrstag"),
        (easter - timedelta(days=2), "Karfreitag"),
        (easter, "Ostersonntag"),
        (easter + timedelta(days=1), "Ostermontag"),
        (date(year, 5, 1), "Tag der Arbeit"),
        (easter + timedelta(days=39), "Christi Himmelfahrt"),
        (easter + timedelta(days=49), "Pfingstsonntag"),
        (easter + timedelta(days=50), "Pfingstmontag"),
        (date(year, 10, 3), "Tag der Deutschen Einheit"),
        (date(year, 10, 31), "Reformationstag"),
        (date(year, 12, 25), "1. Weihnachtsfeiertag"),
        (date(year, 12, 26), "2. Weihnachtsfeiertag"),
    ]
    return [
        {"date": holiday.isoformat(), "name": name, "region": BRANDENBURG}
        for holiday, name in sorted(items)
    ]


def normalize_personnel_code(code: str, portion: float | None = None) -> dict[str, object]:
    """Normalize codes used by both manual entries and imported workbooks."""
    raw = str(code or "").strip()[:12]
    if not raw:
        raise ValueError("Kürzel fehlt")
    standard = {
        "U": ("vacation", 1.0, "Urlaub"),
        "UH": ("vacation", 0.5, "Urlaub"),
        "A": ("work", 1.0, "Arbeit"),
        "AH": ("work", 0.5, "Arbeit"),
        "K": ("sick", 1.0, "Krankheit"),
        "KH": ("sick", 0.5, "Krankheit"),
        "I": ("individual", 1.0, "Individuell"),
        "IH": ("individual", 0.5, "Individuell"),
        "P": ("extra", 1.0, "Zusatzspalte"),
        "PH": ("extra", 0.5, "Zusatzspalte"),
    }
    key = raw.upper()
    if key in standard:
        category, default_portion, label = standard[key]
        canonical = "ph" if key == "PH" else key
    else:
        category, default_portion, label, canonical = "custom", 1.0, "Benutzerdefiniert", raw
    use_portion = default_portion if portion is None else float(portion)
    if use_portion not in (0.5, 1.0):
        raise ValueError("Umfang muss ein ganzer oder halber Tag sein")
    return {
        "code": canonical,
        "category": category,
        "portion": use_portion,
        "label": label,
    }


def _q(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def _safe_xml(raw: bytes, label: str) -> ET.Element:
    head = raw[:2048].upper()
    if b"<!DOCTYPE" in head or b"<!ENTITY" in head:
        raise WorkbookImportError(f"Unsichere XML-Struktur in {label}")
    try:
        return ET.fromstring(raw)
    except ET.ParseError as exc:
        raise WorkbookImportError(f"Beschädigte XML-Struktur in {label}") from exc


def _validate_zip(data: bytes) -> zipfile.ZipFile:
    if not data or len(data) > MAX_WORKBOOK_BYTES:
        raise WorkbookImportError("Die Excel-Datei ist leer oder größer als 5 MB")
    if not data.startswith(b"PK"):
        raise WorkbookImportError("Die Datei ist keine gültige XLSX-Datei")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data), "r")
    except zipfile.BadZipFile as exc:
        raise WorkbookImportError("Die Excel-Datei ist beschädigt") from exc
    infos = archive.infolist()
    if len(infos) > MAX_ZIP_ENTRIES:
        archive.close()
        raise WorkbookImportError("Die Excel-Datei enthält zu viele Bestandteile")
    uncompressed = 0
    for info in infos:
        path = PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts or "\\" in info.filename:
            archive.close()
            raise WorkbookImportError("Die Excel-Datei enthält einen unsicheren Pfad")
        uncompressed += info.file_size
        if uncompressed > MAX_UNCOMPRESSED_BYTES:
            archive.close()
            raise WorkbookImportError("Die Excel-Datei ist entpackt zu groß")
        if info.compress_size and info.file_size > max(1_000_000, info.compress_size * 250):
            archive.close()
            raise WorkbookImportError("Die Excel-Datei weist eine unsichere Kompression auf")
    required = {"xl/workbook.xml", "xl/_rels/workbook.xml.rels"}
    if not required.issubset(set(archive.namelist())):
        archive.close()
        raise WorkbookImportError("Die Excel-Datei enthält keine gültige Arbeitsmappe")
    return archive


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = _safe_xml(archive.read("xl/sharedStrings.xml"), "sharedStrings.xml")
    strings: list[str] = []
    for item in root.findall(_q(MAIN_NS, "si")):
        strings.append("".join(node.text or "" for node in item.iter(_q(MAIN_NS, "t"))))
    return strings


def _sheet_paths(archive: zipfile.ZipFile) -> dict[str, str]:
    workbook = _safe_xml(archive.read("xl/workbook.xml"), "workbook.xml")
    rels = _safe_xml(archive.read("xl/_rels/workbook.xml.rels"), "workbook.xml.rels")
    rel_map = {
        rel.attrib.get("Id", ""): rel.attrib.get("Target", "")
        for rel in rels.findall(_q(REL_NS, "Relationship"))
    }
    result: dict[str, str] = {}
    sheets = workbook.find(_q(MAIN_NS, "sheets"))
    if sheets is None:
        return result
    rel_attr = _q(DOC_REL_NS, "id")
    for sheet in sheets.findall(_q(MAIN_NS, "sheet")):
        name = sheet.attrib.get("name", "")
        target = rel_map.get(sheet.attrib.get(rel_attr, ""), "")
        if not name or not target:
            continue
        if target.startswith("/"):
            normalized = posixpath.normpath(target.lstrip("/"))
        else:
            normalized = posixpath.normpath(posixpath.join("xl", target))
        result[name] = normalized
    return result


CELL_REF_RE = re.compile(r"^([A-Z]+)([1-9][0-9]*)$")


def _column_number(letters: str) -> int:
    value = 0
    for char in letters:
        value = value * 26 + ord(char) - 64
    return value


def _cell_coordinates(reference: str) -> tuple[int, int] | None:
    match = CELL_REF_RE.fullmatch(reference.upper())
    if not match:
        return None
    return _column_number(match.group(1)), int(match.group(2))


def _sheet_cells(archive: zipfile.ZipFile, path: str, shared: list[str]) -> dict[str, object]:
    if path not in archive.namelist():
        raise WorkbookImportError("Ein benötigtes Tabellenblatt fehlt")
    root = _safe_xml(archive.read(path), path)
    cells: dict[str, object] = {}
    for cell in root.iter(_q(MAIN_NS, "c")):
        reference = cell.attrib.get("r", "").upper()
        if not reference:
            continue
        cell_type = cell.attrib.get("t", "")
        if cell_type == "inlineStr":
            value: object = "".join(node.text or "" for node in cell.iter(_q(MAIN_NS, "t")))
        else:
            value_node = cell.find(_q(MAIN_NS, "v"))
            raw = value_node.text if value_node is not None else None
            if raw is None:
                value = ""
            elif cell_type == "s":
                try:
                    value = shared[int(raw)]
                except (ValueError, IndexError):
                    value = ""
            elif cell_type in ("str", "e"):
                value = raw
            elif cell_type == "b":
                value = raw == "1"
            else:
                try:
                    number = float(raw)
                    value = int(number) if number.is_integer() else number
                except ValueError:
                    value = raw
        cells[reference] = value
    return cells


def _text(value: object, limit: int = 160) -> str:
    return str(value or "").strip()[:limit]


def _number(value: object, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return default


def parse_personnel_xlsx(data: bytes, filename: str = "Personalplaner.xlsx") -> dict[str, object]:
    """Parse the Personalplaner-Pro workbook into a normalized import payload."""
    archive = _validate_zip(data)
    try:
        shared = _shared_strings(archive)
        paths = _sheet_paths(archive)
        planner_path = paths.get("Personalplaner")
        if not planner_path:
            raise WorkbookImportError("Das Tabellenblatt „Personalplaner“ fehlt")
        planner = _sheet_cells(archive, planner_path, shared)
        settings = _sheet_cells(archive, paths["Einstellungen"], shared) if "Einstellungen" in paths else {}
    finally:
        archive.close()

    title = _text(planner.get("A1"), 80)
    if "personalplaner" not in title.casefold():
        raise WorkbookImportError("Die Datei entsprcht nicht der Personalplaner-Pro-Vorlage")
    try:
        year = int(_number(planner.get("A4", settings.get("B3")), 0))
    except (TypeError, ValueError):
        year = 0
    if year < 2000 or year > 2100:
        raise WorkbookImportError("Das Planungsjahr konnte nicht eindeutig erkannt werden")
    if "datum" not in _text(planner.get("S12"), 40).casefold():
        raise WorkbookImportError("Die Datumsspalten der Personalplaner-Vorlage wurden nicht erkannt")

    legend_specs = [
        ("G5", "vacation", 1.0, "Urlaub", "U"),
        ("G6", "vacation", 0.5, "Urlaub", "UH"),
        ("J5", "work", 1.0, "Arbeit", "A"),
        ("J6", "work", 0.5, "Arbeit", "AH"),
        ("K5", "sick", 1.0, "Krankheit", "K"),
        ("K6", "sick", 0.5, "Krankheit", "KH"),
        ("Q5", "individual", 1.0, "Individuell", "I"),
        ("Q6", "individual", 0.5, "Individuell", "IH"),
        ("R5", "extra", 1.0, "Zusatzspalte", "P"),
        ("R6", "extra", 0.5, "Zusatzspalte", "ph"),
    ]
    legend: dict[str, dict[str, object]] = {}
    for ref, category, portion, label, fallback in legend_specs:
        workbook_code = _text(planner.get(ref), 12) or fallback
        legend[workbook_code.casefold()] = {
            "code": workbook_code,
            "category": category,
            "portion": portion,
            "label": label,
        }

    employees: list[dict[str, object]] = []
    seen_names: set[str] = set()
    for row in range(14, 14 + MAX_EMPLOYEES):
        name = _text(planner.get(f"B{row}"), 120)
        if not name:
            continue
        name_key = name.casefold()
        if name_key in seen_names:
            raise WorkbookImportError(f"Mitarbeiter „{name}“ ist in der Excel-Datei doppelt vorhanden")
        seen_names.add(name_key)
        employees.append({
            "excel_row": row,
            "name": name,
            "sort_order": len(employees) + 1,
            "carryover_vacation": _number(planner.get(f"D{row}")),
            "annual_vacation": _number((planner.get(f"E"{row}")),
            "entries": [],
        })
    if not employees:
        raise WorkbookImportError("In der Excel-Datei wurden keine Mitarbeiter gefunden")

    total_days = 366 if calendar.isleap(year) else 365
    start_column = _column_number("T")
    unknown_counts: Counter[str] = Counter()
    normalized_counts: Counter[str] = Counter()
    code_counts: Counter[str] = Counter()
    for employee in employees:
        row = int(employee["excel_row"])
        employee_entries = employee["entries"]
        for day_offset in range(total_days):
            column = start_column + day_offset
            number = column
            letters = ""
            while number:
                number, remainder = divmod(number - 1, 26)
                letters = chr(65 + remainder) + letters
            raw_code = _text(planner.get(f"{letters}{row}"), 12)
            if not raw_code:
                continue
            info = legend.get(raw_code.casefold())
            if info is None:
                # Recognize common standard codes even if a customized legend omitted them.
                normalized = normalize_personnel_code(raw_code)
                if normalized["category"] == "custom":
                    unknown_counts[raw_code] += 1
                elif raw_code != normalized["code"]:
                    normalized_counts[f"{raw_code}→{normalized['code']}"] += 1
                info = normalized
            elif raw_code != info["code"]:
                normalized_counts[f"{raw_code}→{info['code']}"] += 1
            canonical = str(info["code"])
            code_counts[canonical] += 1
            employee_entries.append({
                "date": (date(year, 1, 1) + timedelta(days=day_offset)).isoformat(),
                "code": canonical,
                "category": str(info["category"]),
                "portion": float(info["portion"]),
                "label": str(info["label"]),
            })
    warnings: list[str] = []
    for code, count in sorted(unknown_counts.items(), key=lambda item: item[0].casefold()):
        if count == 1:
            warnings.append(f"1 Eintrag mit „{code}“ wird als benutzerdefiniert importiert.")
        else:
            warnings.append(f"{count} Einträge mit „{code}“ werden als benutzerdefiniert importiert.")
    for conversion, count in sorted(normalized_counts.items()):
        noun = "Eintrag wird" if count == 1 else "Einträge werden"
        warnings.append(f"{count} {noun} normalisiert: {conversion}.")

    source_country = _text(settings.get("B4"), 80)
    source_state = _text(settings.get("B5"), 80)
    source_state_code = _text(settings.get("B6"), 12)
    if source_state and source_state.casefold() != BRANDENBURG.casefold():
        warnings.append(
            f"Die Excel-Datei nennt „{source_state}“. Im Werkstattplaner gelten fest die Feiertage für Brandenburg."
        )

    entry_count = sum(len(item["entries"]) for item in employees)
    return {
        "template": title,
        "filename": PurePosixPath(filename.replace("\\", "/")).name[:200] or "Personalplaner.xlsx",
        "sha256": hashlib.sha256(data).hexdigest(),
        "year": year,
        "region": BRANDENBURG,
        "region_code": BRANDENBURG_CODE,
        "source_region": {
            "country": source_country,
            "state": source_state,
            "code": source_state_code,
        },
        "employee_count": len(employees),
        "entry_count": entry_count,
        "code_counts": dict(sorted(code_counts.items(), key=lambda item: item[0].casefold())),
        "unknown_codes": dict(sorted(unknown_counts.items(), key=lambda item: item[0].casefold())),
        "warnings": warnings,
        "employees": employees,
    }
