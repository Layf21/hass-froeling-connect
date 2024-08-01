"""Platform for Fröling Connect integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION
from .coordinator import (
    FroelingConnectConfigEntry,
    FroelingConnectDataUpdateCoordinator,
)

binary_sensor_deviceclass_mapping = {}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FroelingConnectConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add Froeling Connect entities from a config_entry."""
    coordinator = entry.runtime_data

    entities = []
    for idx, param in coordinator.data.parameters.items():
        if param.parameter_type != "NumValueObject" or param.editable:
            continue
        if param.min_val == "0" and param.max_val == "1" and param.unit == "":
            entities.append(FroelingConnectBinarySensor(coordinator, idx))

    async_add_entities(entities)


class FroelingConnectBinarySensor(
    CoordinatorEntity[FroelingConnectDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of a BinarySensor."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FroelingConnectDataUpdateCoordinator,
        idx: tuple[int, str, str],
    ) -> None:
        """Initialize binary_sensor platform for Froeling Connect integration."""
        super().__init__(coordinator, context=idx)

        self._idx = idx  # (facility_id, component_id, parameter_id)

        parameter = coordinator.data.parameters[idx]
        component = coordinator.components[idx[0]][idx[1]]
        self.parameter = parameter
        self.component = component

        self._attr_name = parameter.display_name
        self._attr_unique_id = f"{idx[0]}_{idx[1]}_{idx[2]}"
        self.entity_id = generate_entity_id(
            "binary_sensor.{}",
            f"{idx[0]}_{component.display_name}_{parameter.name}",
            hass=coordinator.hass,
        )

        self._attr_device_info = self.coordinator.component_device_info[
            (self._idx[0], self._idx[1])
        ]

        self._attr_is_on = parameter.value == "1"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        parameter = self.coordinator.data.parameters[self._idx]
        self._attr_is_on = parameter.value == "1"
        self.parameter = parameter

        self.async_write_ha_state()
