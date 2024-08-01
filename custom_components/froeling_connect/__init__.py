"""The Fröling Connect integration."""

from __future__ import annotations

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant

from .const import PLATFORMS
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

    async def close_froeling(event: Event) -> None:
        await coordinator.froeling.session.close()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, close_froeling)
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: FroelingConnectConfigEntry
) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.froeling.session.close()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
