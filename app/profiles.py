"""Read-only Grow-Central culture profile library."""
from __future__ import annotations

import html
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])
DATA_FILE = Path(__file__).resolve().parents[1] / "config" / "grow_profiles.json"


def _library() -> dict:
    try:
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(500, "Profilbibliothek ist nicht lesbar") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("profiles"), list):
        raise HTTPException(500, "Profilbibliothek hat ein ungültiges Format")
    return payload


def _profile(profile_id: str) -> dict:
    for item in _library()["profiles"]:
        if item.get("id") == profile_id:
            return item
    raise HTTPException(404, "Profil nicht gefunden")


@router.get("")
async def list_profiles(category: str | None = None, q: str | None = Query(default=None, max_length=80)):
    library = _library()
    rows = library["profiles"]
    if category:
        rows = [row for row in rows if category.casefold() in str(row.get("category", "")).casefold()]
    if q:
        needle = q.casefold()
        rows = [row for row in rows if needle in " ".join([
            str(row.get("name", "")), str(row.get("scientific_name", "")),
            str(row.get("category", "")), str(row.get("summary", "")),
        ]).casefold()]
    summaries = [{
        "id": row.get("id"), "name": row.get("name"),
        "scientific_name": row.get("scientific_name"), "category": row.get("category"),
        "difficulty": row.get("difficulty"), "light_need": row.get("light_need"),
        "systems": row.get("systems", []), "summary": row.get("summary", ""),
        "phase_count": len(row.get("phases", [])),
    } for row in rows]
    return {"schema_version": library.get("schema_version", 1), "profiles": summaries}


@router.get("/{profile_id}")
async def get_profile(profile_id: str):
    row = _profile(profile_id)
    return {"profile": row, "policy": {
        "type": "guidance",
        "automation_requires_confirmation": True,
        "note": "Profilwerte sind Start- und Orientierungswerte; Sorte, System und reale Messwerte können Anpassungen erfordern.",
    }}


@router.get("/{profile_id}/checklist")
async def get_checklist(profile_id: str, phase: str | None = None):
    row = _profile(profile_id)
    phases = row.get("phases", [])
    if phase:
        phases = [item for item in phases if item.get("id") == phase]
        if not phases:
            raise HTTPException(404, "Phase nicht gefunden")
    tasks = []
    for phase_row in phases:
        for index, text in enumerate(phase_row.get("todos", []), start=1):
            tasks.append({
                "id": f"{profile_id}:{phase_row.get('id')}:{index}",
                "phase_id": phase_row.get("id"),
                "phase": phase_row.get("title"),
                "text": text,
            })
    return {"profile_id": profile_id, "profile_name": row.get("name"), "tasks": tasks, "printable": True}


@router.get("/{profile_id}/print", response_class=HTMLResponse)
async def printable_profile(profile_id: str):
    row = _profile(profile_id)
    esc = html.escape
    phase_html = []
    for phase in row.get("phases", []):
        todos = "".join(f'<li><span class="box"></span>{esc(str(item))}</li>' for item in phase.get("todos", []))
        targets = "".join(f'<li><b>{esc(str(k))}:</b> {esc(str(v))}</li>' for k, v in phase.get("targets", {}).items())
        target_block = f'<ul class="targets">{targets}</ul>' if targets else ""
        phase_html.append(f'<section><h2>{esc(str(phase.get("title", "")))}</h2><ul class="todos">{todos}</ul>{target_block}</section>')
    systems = ", ".join(map(str, row.get("systems", [])))
    sources = "".join(f'<li>{esc(str(src.get("label", "Quelle")))}</li>' for src in row.get("sources", []))
    body = f'''<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Grow-Central Profil – {esc(str(row.get("name", "")))}</title>
<style>@page{{size:A4;margin:14mm}}body{{font-family:Arial,sans-serif;color:#132017;max-width:900px;margin:auto}}header{{border-bottom:4px solid #4f8f2f;padding-bottom:12px}}h1{{font-size:28px;margin:0 0 5px}}.meta{{color:#526258}}section{{break-inside:avoid;border:1px solid #dce8d8;border-radius:10px;padding:12px 16px;margin:12px 0}}h2{{color:#2f6f24;font-size:18px;margin:0 0 8px}}ul{{padding-left:0;list-style:none}}li{{margin:8px 0}}.box{{display:inline-block;width:14px;height:14px;border:1.5px solid #2f6f24;margin-right:9px;vertical-align:-2px}}.targets{{background:#f4f8f2;padding:8px 12px;border-radius:8px}}footer{{font-size:11px;color:#66756b;border-top:1px solid #d8e2d5;margin-top:18px;padding-top:10px}}@media print{{.noprint{{display:none}}}}</style></head><body>
<header><h1>Grow-Central Basisprofil – {esc(str(row.get("name", "")))}</h1><div class="meta"><b>{esc(str(row.get("scientific_name", "")))}</b> · {esc(str(row.get("category", "")))} · Systeme: {esc(systems)}</div><p>{esc(str(row.get("summary", "")))}</p></header>
<div class="noprint" style="margin:14px 0"><button onclick="window.print()">Drucken / als PDF speichern</button></div>
{''.join(phase_html)}
<section><h2>Quellenbasis</h2><ul>{sources}</ul></section>
<footer>Hinweis: Profilwerte sind Start- und Orientierungswerte. Sorte, System, Standort und reale Messwerte können Anpassungen erfordern.</footer></body></html>'''
    return HTMLResponse(body)
