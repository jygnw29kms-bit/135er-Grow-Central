"""Universal device platform for 135er-Grow Central.

The device layer deliberately separates Grow Central entities/capabilities from
vendor transports. Provider implementations may be local, cloud, gateway or
bridge based without leaking vendor-specific details into automations or GUIs.
"""

from .catalog import PROVIDERS, provider_catalog
from .models import Capability, DeviceClass, ProviderDescriptor, SupportLevel, Transport

__all__ = [
    "Capability",
    "DeviceClass",
    "ProviderDescriptor",
    "SupportLevel",
    "Transport",
    "PROVIDERS",
    "provider_catalog",
]
