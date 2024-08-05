"""Platform for Fröling Connect integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CONF_SEND_CHANGES, LOGGER
from .coordinator import (
    FroelingConnectConfigEntry,
    FroelingConnectDataUpdateCoordinator,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FroelingConnectConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add Froeling Connect entities from a config_entry."""
    coordinator = entry.runtime_data

    entities = []
    for idx, param in coordinator.data.parameters.items():
        if param.parameter_type != "StringValueObject":
            continue  # Use number or sensor instead
        if not param.editable or not entry.data[CONF_SEND_CHANGES]:
            continue  # use sensor instead
        if not param.string_list_key_values:
            LOGGER.warning(
                "Unexpected parameter data: %s[%s] value mapping is: %s",
                param.name,
                param.id,
                param.string_list_key_values,
            )
            continue  # should not happen, type is StringValueObject but no strings are given
        entities.append(
            FroelingConnectNumber(coordinator, idx, entry.data[CONF_SEND_CHANGES])
        )

    async_add_entities(entities)


class FroelingConnectNumber(
    CoordinatorEntity[FroelingConnectDataUpdateCoordinator], SelectEntity
):
    """Representation of a Sensor."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FroelingConnectDataUpdateCoordinator,
        idx: tuple[int, str, str],
        send_changes: bool = True,
    ) -> None:
        """Initialize select entity for Froeling Connect integration."""
        super().__init__(coordinator, context=idx)

        self._idx = idx  # (facility_id, component_id, parameter_id)
        self.send_changes = send_changes

        parameter = coordinator.data.parameters[idx]
        component = coordinator.components[idx[0]][idx[1]]
        self.parameter = parameter
        self._attr_name = parameter.display_name
        self._attr_unique_id = f"{idx[0]}_{idx[1]}_{idx[2]}"
        self.entity_id = generate_entity_id(
            "select.{}",
            f"{idx[0]}_{component.display_name}_{parameter.name}",
            hass=coordinator.hass,
        )

        self._attr_device_info = self.coordinator.component_device_info[
            (self._idx[0], self._idx[1])
        ]

        self._attr_options = list(parameter.string_list_key_values.values())

        self._set_current_option()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._set_current_option()
        self.async_write_ha_state()

    def _set_current_option(self) -> str:
        """Set the current string value."""
        parameter = self.coordinator.data.parameters[self._idx]
        if str(parameter.value) in parameter.string_list_key_values:
            self._attr_current_option = parameter.string_list_key_values[
                str(parameter.value)
            ]
        else:
            self._attr_current_option = str(parameter.value)

    async def async_select_option(self, option: str) -> None:
        """Set new value."""
        if not self.send_changes:
            LOGGER.info("Did not set value for %s", self.name)
            return

        if option not in self.parameter.string_list_key_values.values():
            raise ServiceValidationError(
                f"{option} is not a valid state for {self.parameter.name}"
            )
        number_value = next(
            key
            for key, value in self.parameter.string_list_key_values.items()
            if value == str(option)
        )
        LOGGER.debug("New value for %s is %s (%s)", self.name, option, number_value)
        await self.parameter.set_value(str(number_value))
