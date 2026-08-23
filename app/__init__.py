"""135er-Grow Central application package."""

# Install the Grow Central camera policy once at package import. Importing the
# camera module here is deliberate: later imports receive the already-patched
# generic UVC backend without duplicating camera logic.
from app import camera as _camera
from app.camera_policy import install as _install_camera_policy

_install_camera_policy(_camera)

del _camera, _install_camera_policy
