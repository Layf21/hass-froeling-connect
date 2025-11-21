"""The Fröling Connect integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, ServiceCall, callback

from froeling.datamodels.timewindow import TimeWindows

from .const import DOMAIN, PLATFORMS, CONF_SEND_CHANGES
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

    async def handle_set_timewindows(call: ServiceCall) -> None:
        """Set timewindows for Froeling Connect facilities."""
        if not entry.data[CONF_SEND_CHANGES]:
            raise RuntimeError("Sending changes is disabled. Service won't run.")
        facility = await entry.runtime_data.froeling.get_facility(
            call.data["facility_id"]
        )
        await facility.update_time_windows(
            TimeWindows._from_list(call.data["timewindows"])  # noqa: SLF001
        )

    if entry.data[CONF_SEND_CHANGES]:
        hass.services.async_register(DOMAIN, "set_timewindows", handle_set_timewindows)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: FroelingConnectConfigEntry
) -> bool:
    """Unload a config entry."""

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
