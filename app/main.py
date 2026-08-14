"""135er-Grow Central Local API alpha-0.7.5.

DE: Lokaler Raspberry-Pi-Dienst fÃ¼r Mars Hydro/iConnect, Smart Home,
Netzwerkverwaltung, BLE-Diagnose und die lokale WeboberflÃ¤che.
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any

from bleak import BleakClient, BleakScanner
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.security import require_write_auth
from app.diagnostics import router as diagnostics_router
from app.smarthome.router import router as smarthome_router
from app.network import router as network_router
from app.mars_hydro import is_mars_hydro_ble_candidate, public_hardware_profile
from app.system_info import router as system_router

NAME_HINT = os.getenv("DF100M_NAME_HINT", "MZ_MZF002")
WRITE_UUID = os.getenv("DF100M_WRITE_UUID", "f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d")
NOTIFY_UUID = os.getenv("DF100M_NOTIFY_UUID", "83677baa-3eb8-4866-b6b6-96e5ed5cc48d")
SPEED_MODE = os.getenv("DF100M_SPEED_MODE", "byte")
ALLOW_WRITES = os.getenv("DF100M_ALLOW_WRITES", "false").lower() == "true"
ALLOW_RAW_WRITES = os.getenv("DF100M_ALLOW_RAW_WRITES", "false").lower() == "true"

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="135er-Grow Central Local", version="0.7.5")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
app.include_router(network_router)
app.include_router(smarthome_router)
app.include_router(diagnostics_router)
app.include_router(system_router)

client: BleakClient | None = None
current_address: str | None = None
notifications: list[dict[str, Any]] = []
logger = logging.getLogger(__name__)


class ConnectBody(BaseModel):
    address: str = Field(min_length=2, max_length=128)


class SpeedBody(BaseModel):
    percent: int = Field(ge=0, le=100)


class RawBody(BaseModel):
    uuid: str = Field(min_length=4, max_length=64, pattern=r"^[0-9a-fA-F-]+$")
    hex: str = Field(min_length=2, max_length=383, pattern=r"^[0-9a-fA-F\s]+$")
    response: bool = True


def speed_payload(percent: int) -> bytes:
    if not 0 <= percent <= 100:
        raise ValueError("percent must be 0..100")
    if SPEED_MODE == "byte":
        return bytes([percent])
    if SPEED_MODE == "ascii":
        return str(percent).encode("ascii")
    if SPEED_MODE == "hexprefix":
        return bytes([0x01, percent])
    raise ValueError(f"unknown speed mode: {SPEED_MODE}")


def _status_payload() -> dict[str, Any]:
    online = bool(client and client.is_connected)
    return {
        "connected": online,
        "online": onomøã[h‘éì¶»§q«^u…µ•É…}¥ô‰…´Àˆ°½¹ÑÉ½°ô‰Í¡•±±}½µµ…¹ˆ°Ù…±Õ”ôÄ¤(€€€Ý¥Ñ ÁåÑ•ÍÐ¹É…¥Í•Ì¡Y…±Õ•ÉÉ½È¤è(€€€€€€€…µ•É„¹}Í•Ñ}½¹ÑÉ½±}Íå¹Œ¡É•ÅÕ•ÍÐ¤(()‘•˜Ñ•ÍÑ}…µ•É…}½¹ÑÉ½±}ÝÉ¥Ñ•}¡•­Í}É…¹”¡µ½¹­•åÁ…Ñ ¤è(€€€µ½¹­•åÁ…Ñ ¹Í•Ñ…ÑÑÈ¡…µ•É„°€‰}½¹ÑÉ½±Í}Íå¹Œˆ°±…µ‰‘„}…µ•É…}¥èì(€€€€€€€€‰‘•Ù¥”ˆè€ˆ½‘•Ø½Ù¥‘•¼Àˆ°(€€€€€€€€‰½¹ÑÉ½±Ìˆèmì‰¹…µ”ˆè€‰‰É¥¡Ñ¹•ÍÌˆ°€‰ÝÉ¥Ñ…‰±”ˆèQÉÕ”°€‰µ¥¸ˆè€À°€‰µ…àˆè€ÈÔÔ°€‰µ•¹Ôˆèmt°€‰Ù…±Õ”ˆè€ÄÈáõt°(€€€ô¤(€€€É•ÅÕ•ÍÐ€ô…µ•É„¹…µ•É…½¹ÑÉ½±I•ÅÕ•ÍÐ¡…µ•É…}¥ô‰…´Àˆ°½¹ÑÉ½°ô‰‰É¥¡Ñ¹•ÍÌˆ°Ù…±Õ”ôäää¤(€€€Ý¥Ñ ÁåÑ•ÍÐ¹É…¥Í•Ì¡Y…±Õ•ÉÉ½È¤è(€€€€€€€…µ•É„¹}Í•Ñ}½¹ÑÉ½±}Íå¹Œ¡É•ÅÕ•ÍÐ¤(()‘•˜Ñ•ÍÑ}•¹ÑÉåÁ½¥¹Ñ}•áÁ½Í•Í}…µ•É…}…¹‘}±½¥¹}Í½ÕÉ•Ì ¤è(€€€•¹ÑÉåÁ½¥¹Ð€ô€¡}}¥µÁ½ÉÑ}| ‰Á…Ñ¡±¥ˆˆ¤¹A…Ñ ¡}}™¥±•}|¤¹Á…É•¹ÑÍlÅt€¼€‰…ÁÀˆ€¼€‰•¹ÑÉåÁ½¥¹Ð¹Áäˆ¤¹É•…‘}Ñ•áÐ¡•¹½‘¥¹œô‰ÕÑ˜´àˆ¤(€€€…ÍÍ•ÉÐ€‰Õ¥ÕÑ¡5¥‘‘±•Ý…É”ˆ¥¸•¹ÑÉåÁ½¥¹Ð(€€€…ÍÍ•ÉÐ€‰…µ•É…}É½ÕÑ•Èˆ¥¸•¹ÑÉåÁ½¥¹Ð(€€€…ÍÍ•ÉÐ€‰¥¹±Õ‘•}É½ÕÑ•È¡…µ•É…}É½ÕÑ•È¤ˆ¥¸•¹ÑÉåÁ½¥¹Ð(()‘•˜Ñ•ÍÑ}ÍåÍÑ•µ}¥‘•¹Ñ¥Ñå}É•…‘Í}‘•Ñ•Ñ•‘}µ½‘•±}…¹‘}‰Õ¥±¡µ½¹­•åÁ…Ñ °ÑµÁ}Á…Ñ ¤è(€€€µ½‘•°€ôÑµÁ}Á…Ñ €¼€‰µ½‘•°ˆ(€€€µ½‘•°¹ÝÉ¥Ñ•}‰åÑ•Ì¡ˆ‰I…ÍÁ‰•ÉÉäA¤€Ð5½‘•°I•Ø€Ä¸ÑqàÀÀˆ¤(€€€…ÍÍ•ÉÐÍåÍÑ•µ}¥¹™¼¹}Ñ•áÐ¡µ½‘•°°€‰™…±±‰…¬ˆ¤€ôô€‰I…ÍÁ‰•ÉÉäA¤€Ð5½‘•°I•Ø€Ä¸Ðˆ(€€€µ¥ÍÍ¥¹œ€ôÑµÁ}Á…Ñ €¼€‰µ¥ÍÍ¥¹œˆ(€€€…ÍÍ•ÉÐÍåÍÑ•µ}¥¹™¼¹}Ñ•áÐ¡µ¥ÍÍ¥¹œ°€‰™…±±‰…¬ˆ¤€ôô€‰™…±±‰…¬ˆ(()‘•˜Ñ•ÍÑ}…µ•É…}ÍÑÉ•…µ}É½ÕÑ•}¥Í}•áÁ½Í• ¤è(€€€Á…Ñ¡Ì€ô€¡}}¥µÁ½ÉÑ}| ‰…ÁÀ¹•¹ÑÉåÁ½¥¹Ðˆ°™É½µ±¥ÍÐõl‰…ÁÀ‰t¤¹…ÁÀ¹½Á•¹…Á¤ ¥l‰Á…Ñ¡Ì‰t¤(€€€…ÍÍ•ÉÐ€ˆ½…Á¤½ØÄ½…µ•É„½ÍÑÉ•…´ˆ¥¸Á…Ñ¡Ì(€€€…ÍÍ•ÉÐ€ˆ½…Á¤½ØÄ½ÍåÍÑ•´½¥¹™¼ˆ¥¸Á…Ñ¡Ì(