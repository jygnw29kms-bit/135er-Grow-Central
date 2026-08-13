"""Production entry point for the Raspberry Pi appliance."""
from app.main import app
from app.gui_auth import GuiAuthMiddleware, router as gui_auth_router

app.add_middleware(GuiAuthMiddleware)
app.include_router(gui_auth_router)
