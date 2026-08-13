"""Production entry point for the Raspberry Pi appliance."""
from app.main import app
from app.camera import router as camera_router
from app.gui_auth import GuiAuthMiddleware, router as gui_auth_router
from app.firstboot import router as firstboot_router

app.add_middleware(GuiAuthMiddleware)
app.include_router(gui_auth_router)
app.include_router(camera_router)
app.include_router(firstboot_router)
