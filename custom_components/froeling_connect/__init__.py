"""The Fröling Connect integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import service

from .const import CONF_SEND_CHANGES, DOMAIN, PLATFORMS
from .coordinator import (
    FroelingConnectConfigEntry,
    FroelingConnectDataUpdateCoordinator,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: FroelingConnectConfigEntry
) -> bool:
    """Set up Fröling Connect from a config entry."""

    coordinator = FroelingConnectDataUpdateCoordinator(hass, entry.entry_id)
    await coordinator.async_setup()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if entry.data[CONF_SEND_CHANGES]:
        service.async_register_platform_entity_service(
            hass,
            DOMAIN,
            "set_timewindows",
            entity_domain="sensor",
            schema={vol.Required("timewindows"): list[dict]},
            func="set_timewindows",
        )
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: FroelingConnectConfigEntry
) -> bool:
    """Unload a config entry."""

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
