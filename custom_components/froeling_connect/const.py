"""Constants for the Fröling Connect integration."""

from __future__ import annotations

import logging
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "froeling_connect"
LOGGER: Final[logging.Logger] = logging.getLogger(__package__)
PLATFORMS: Final[list[Platform]] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
]
ATTRIBUTION: Final = "Data provided by Froeling Connect"
CONF_SEND_CHANGES: Final = "send_changes"
