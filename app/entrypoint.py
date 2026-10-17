"""Production entry point for the headless Raspberry Pi appliance."""
from app.main import app
from app import camera as _camera
from app.camera_policy import install as _install_camera_policy
from app.camera import router as camera_router
from app.camera_led import install as install_camera_led
from app.automation import router as automation_router, install as install_automation
from app.recipes import router as recipes_router
from app.timelapse import router as timelapse_router
from app.recordings import router as recordings_router
from app.grow_photos import router as grow_photos_router
from app.grow_photo_ui import GrowPhotoUiMiddleware
from app.auth_middleware import GuiAuthMiddleware
from app.gui_auth import router as gui_auth_router
from app.firstboot import router as firstboot_router
from app.gui_shell import router as gui_shell_router
from app.ui_layout import router as ui_layout_router
from app.mdns_alias import install as install_mdns_alias
from app.rooms import router as rooms_router, install as install_rooms
from app.cloud_status import router as cloud_status_router
from app.devices.gc_pairing import install_observer
from app.devices.gc_calibration import router as calibration_router
from app.provisioning.ble import install_observer as install_ble_observer
from app.runtime_health import router as runtime_health_router
from app.maintenance import router as maintenance_router
from app.grow_alerts import router as grow_alerts_router
from app.edition import router as edition_router
from app.setup_portal import SetupPortalMiddleware

_install_camera_policy(_camera)
del _camera, _install_camera_policy

install_camera_led()
app.add_middleware(GuiAuthMiddleware)
# Added after auth on purpose: Starlette makes this the outer layer, so an
# unprovisioned device can answer captive-portal probes and setup requests
# before normal GUI/API authentication exists.
app.add_middleware(SetupPortalMiddleware)
# The photo enhancement is injected only into the approved product HTML shell;
# setup/captive/legacy responses are positively excluded by the middleware.
app.add_middleware(GrowPhotoUiMiddleware)
# No kiosk/touch HTML rewriting is used anymore. Browser and mobile clients
# provide their native input methods and receive responses byte-for-byte.
app.include_router(gui_auth_router)
app.include_router(gui_shell_router)
app.include_router(ui_layout_router)
app.include_router(camera_router)
app.include_router(automation_router)
app.include_router(recipes_router)
app.include_router(timelapse_router)
app.include_router(recordings_router)
app.include_router(grow_photos_router)
app.include_router(firstboot_router)
app.include_router(rooms_router)
app.include_router(cloud_status_router)
app.include_router(runtime_health_router)
app.include_router(maintenance_router)
app.include_router(grow_alerts_router)
app.include_router(edition_router)
app.include_router(calibration_router)
install_mdns_alias(app)
install_rooms(app)
install_automation(app)

install_observer(app)
install_ble_observer(app)
