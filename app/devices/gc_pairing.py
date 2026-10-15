"""Manual acceptance endpoints. Discovery never implies authorization."""
import asyncio
from types import SimpleNamespace
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StrictBool, field_validator
from app.security import require_write_auth
from .gc_trust import TrustStore
from .gc_calibration import CalibrationStore

router = APIRouter(prefix='/api/devices/trust', tags=['sensor-pairing'])

class Acceptance(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    room_id: str = Field(min_length=1, max_length=80)
    fingerprint_confirmation: str = Field(pattern=r'^(?:[a-fA-F0-9]{16}|[a-fA-F0-9]{64})$')
    identity_confirmed: StrictBool = False

    @field_validator('name')
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('sensor name must not be blank')
        return value


@router.get('', dependencies=[Depends(require_write_auth)])
async def list_sensors():
    return {'devices': await asyncio.to_thread(TrustStore().list),
            'provisioning': {'primary': 'usb', 'ble_available': True, 'credential_transfer': 'usb_primary_ble_recovery', 'ble_setup': '/api/devices/ble', 'usb_setup': '/api/devices/usb'}}


async def _fresh_identity_proof(provider, device_id: str, expected: dict | None):
    """Prefer network proof, but allow an equally fresh physical USB proof during onboarding."""
    try:
        return await provider.prove_identity(device_id), 'mqtt'
    except TimeoutError as mqtt_timeout:
        # A newly flashed/provisioned sensor can be physically attached while its
        # TLS/MQTT session is not ready yet. The USB path issues its own random
        # 256-bit challenge and verifies the signed P-256 response, so this is a
        # transport fallback, not an identity bypass.
        from app.provisioning.usb_identity import prove_connected_device
        try:
            usb = await asyncio.to_thread(prove_connected_device, device_id)
        except TimeoutError:
            raise mqtt_timeout
        if not expected or usb.public_key != expected.get('public_key') or usb.fingerprint != expected.get('fingerprint'):
            raise PermissionError('USB-Sensoridentität passt nicht zur zuvor entdeckten Identität.')
        proof = SimpleNamespace(
            public_key=usb.public_key,
            body={
                'hardware_uid': usb.hardware_uid,
                'calibration': usb.calibration,
                'state': {'meta': {'firmware': usb.firmware}},
            },
        )
        return proof, 'usb'


@router.post('/{device_id}/accept', dependencies=[Depends(require_write_auth)])
async def accept_sensor(device_id: str, body: Acceptance):
    from app import rooms
    from .runtime import runtime
    try:
        expected = await asyncio.to_thread(TrustStore().get, device_id)
        confirmation = body.fingerprint_confirmation.lower()
        if len(confirmation) == 64:
            if not body.identity_confirmed or not expected or confirmation != expected['fingerprint']:
                raise PermissionError('Sensoridentität zuerst ausdrücklich bestätigen; bei geänderter Identität neu prüfen.')
        room_state = rooms.load_state()
        rooms.room_or_404(room_state, body.room_id)
        proof, identity_transport = await _fresh_identity_proof(runtime.get('growcentral_esp32'), device_id, expected)
        metadata = (expected or {}).get('metadata') or {}
        if 'soil_moisture' in metadata.get('capabilities', []):
            state = proof.body.get('state') or {}
            meta = state.get('meta') if isinstance(state, dict) else {}
            firmware = meta.get('firmware') if isinstance(meta, dict) else metadata.get('firmware')
            CalibrationStore().require_valid(device_id, fingerprint=(expected or {}).get('fingerprint'),
                public_key=proof.public_key, hardware_uid=proof.body.get('hardware_uid'), firmware_version=firmware)
            if not (proof.body.get('calibration') or {}).get('ready'):
                CalibrationStore().invalidate(device_id, 'sensor reports calibration incomplete')
                raise PermissionError('Bodenfeuchtesensor muss zuerst den USB-Kalibrierablauf vollständig abschließen.')
        def assign():
            with rooms.edit_state() as current:
                rooms.room_or_404(current, body.room_id)
                current['assignments'][f'growcentral_esp32:{device_id}'] = body.room_id
        row = await asyncio.to_thread(TrustStore().accept, device_id, name=body.name, room_id=body.room_id,
                                      fingerprint=confirmation[-16:], proved_key=proof.public_key, assign=assign)
        return {'ok': True, 'device': row, 'credential_transfer': 'disabled', 'identity_transport': identity_transport}
    except KeyError as exc:
        raise HTTPException(404, 'Sensor nicht gefunden') from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(504, 'Sensor bestätigt seine Identität weder über MQTT noch über eine direkte USB-Verbindung; Firmware, TLS/MQTT und Verbindung prüfen') from exc


def _remove_room_assignment(device_id: str) -> None:
    # Trust state is authoritative, but stale room assignments would still
    # inflate room counters and confuse the operator after revoke/reject.
    from app import rooms
    global_id = f'growcentral_esp32:{device_id}'
    with rooms.edit_state() as state:
        state['assignments'].pop(global_id, None)


async def _transition(device_id, status):
    try:
        row = await asyncio.to_thread(TrustStore().transition, device_id, status)
        # The security decision is persisted first. Cleanup is deliberately
        # secondary: a room storage failure must never undo a revocation.
        try:
            await asyncio.to_thread(_remove_room_assignment, device_id)
        except OSError:
            pass
        return {'ok': True, 'device': row}
    except KeyError as exc:
        raise HTTPException(404, 'Sensor nicht gefunden') from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post('/{device_id}/reject', dependencies=[Depends(require_write_auth)])
async def reject_sensor(device_id: str):
    return await _transition(device_id, 'REJECTED')


@router.post('/{device_id}/revoke', dependencies=[Depends(require_write_auth)])
async def revoke_sensor(device_id: str):
    return await _transition(device_id, 'REVOKED')


@router.post('/{device_id}/release', dependencies=[Depends(require_write_auth)])
async def release_sensor(device_id: str):
    return await _transition(device_id, 'DISCOVERED')


class IdentityReset(BaseModel):
    fingerprint_confirmation: str = Field(pattern=r'^(?:[a-fA-F0-9]{16}|[a-fA-F0-9]{64})$')
    identity_confirmed: StrictBool = False


@router.post('/{device_id}/reset-identity', dependencies=[Depends(require_write_auth)])
async def reset_sensor_identity(device_id: str, body: IdentityReset):
    try:
        confirmation = body.fingerprint_confirmation.lower()
        if len(confirmation) == 64:
            expected = await asyncio.to_thread(TrustStore().get, device_id)
            if not body.identity_confirmed or not expected or confirmation != expected['fingerprint']:
                raise PermissionError('Zurücksetzen der bisherigen Identität ausdrücklich bestätigen.')
        row = await asyncio.to_thread(TrustStore().reset_identity, device_id, confirmation[-16:])
        try:
            await asyncio.to_thread(CalibrationStore().invalidate, device_id, 'device identity reset')
        except OSError:
            pass
        return {'ok': True, 'device': row}
    except KeyError as exc:
        raise HTTPException(404, 'Sensor nicht gefunden') from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


def install_observer(app):
    """Retained announcements become visible even without an open browser."""
    if getattr(app.state, "sensor_observer_installed", False):
        return
    app.state.sensor_observer_installed = True
    from .runtime import runtime
    import contextlib

    async def observe():
        provider = runtime.get('growcentral_esp32')
        from .gc_esp32_protocol import device_topic, wildcard_topic
        while True:
            try:
                async with provider._client() as client:
                    await client.subscribe(wildcard_topic(provider.root, 'announce'))
                    async for incoming in client.messages:
                        try:
                            if len(incoming.payload) > 8192:
                                continue
                            announce, signed = provider._decode_announcement(bytes(incoming.payload))
                            if str(incoming.topic) != device_topic(provider.root, announce.id, 'announce'):
                                continue
                            await asyncio.to_thread(TrustStore().discover, announce, signed)
                        except (ValueError, PermissionError, UnicodeError):
                            continue
            except Exception:
                # Network failures never stop local measurements or the application.
                await asyncio.sleep(5)

    async def start():
        app.state.sensor_observer = asyncio.create_task(observe())

    async def stop():
        task = getattr(app.state, 'sensor_observer', None)
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    app.router.add_event_handler('startup', start)
    app.router.add_event_handler('shutdown', stop)
