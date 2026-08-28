"""135er-Grow Central application package.

Package imports intentionally have no runtime side effects. Lightweight helpers
such as the first-boot configurator import ``app.hardware`` with system Python
before the web stack is involved; importing this package must therefore not pull
in FastAPI or camera dependencies.
"""
