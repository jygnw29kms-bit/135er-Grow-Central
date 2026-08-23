"""Production entry point for the Raspberry Pi appliance."""
from app.main import app
from app.camera import router as camera_router
from app.automation import router as automation_router
from app.gui_auth import GuiAuthMiddleware, router as gui_auth_router
from app.firstboot import router as firstboot_router
from app.gui_shell import router as gui_shell_router
from app.mdns_alias import install as install_mdns_alias
from app.rooms import router as rooms_router, install as install_rooms

app.add_middleware(GuiAuthMiddleware)
app.include_router(gui_auth_router)
app.include_router(gui_shell_router)
app.include_router(camera_router)
app.include_router(automation_router)
app.include_router(firstboot_router)
app.include_router(rooms_router)
install_mdns_alias(app)
install_rooms(app)
