"""Production entry point for the Raspberry Pi appliance."""
from app.main import app
from app import camera as _camera
from app.camera_policy import install as _install_camera_policy
from app.camera import router as camera_router
from app.camera_led import install as install_camera_led
from app.automation import router as automation_router
from app.gui_auth import GuiAuthMiddleware, router as gui_auth_router
from app.firstboot import router as firstboot_router
from app.gui_shell import router as gui_shell_router
from app.mdns_alias import install as install_mdns_alias
from app.rooms import router as rooms_router, install as install_rooms
from app.cloud_status import router as cloud_status_router
from app.setup_portal import SetupPortalMiddleware
from app.touch_keyboard import TouchKeyboardMiddleware

_install_camera_policy(_camera)
del _camera, _install_camera_policy

install_camera_led()
app.add_middleware(GuiAuthMiddleware)
# Added after auth on purpose: Starlette makes this the outer layer, so an
# unprovisioned device can answer captive-portal probes and setup requests
# before normal GUI authentication exists.
app.add_middleware(SetupPortalMiddleware)
# Outermost HTML post-processing layer: First Boot, Login and the normal UI all
# receive the same local touch keyboard without a desktop Onboard dependency.
app.add_middleware(TouchKeyboardMiddleware)
app.include_router(gui_auth_router)
app.include_router(gui_shell_router)
app.include_router(camera_router)
app.include_router(automation_router)
app.include_router(firstboot_router)
app.include_router(rooms_router)
app.include_router(cloud_status_router)
install_mdns_alias(app)
install_rooms(app)
