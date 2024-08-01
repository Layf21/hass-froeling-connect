"""Platform for Fröling Connect integration."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, LOGGER
from .coordinator import (
    FroelingConnectConfigEntry,
    FroelingConnectDataUpdateCoordinator,
)

device_class_unit_mapping: dict[str, str] = {
    "°C": (NumberDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS),
    "°F": (NumberDeviceClass.TEMPERATURE, UnitOfTemperature.FAHRENHEIT),
    "h": (NumberDeviceClass.DURATION, UnitOfTime.HOURS),
    "": (None, None),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FroelingConnectConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add Froeling Connect entities from a config_entry."""
    coordinator = entry.runtime_data

    entities = []
    for idx, param in coordinator.data.parameters.items():
        if param.parameter_type != "NumValueObject" or not param.editable:
            continue
        if param.min_val == "0" and param.max_val == "1" and param.unit == "":
            continue
        entities.append(FroelingConnectNumber(coordinator, idx))

    async_add_entities(entities)


class FroelingConnectNumber(
    CoordinatorEntity[FroelingConnectDataUpdateCoordinator], NumberEntity
):
    """Representation of a Sensor."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FroelingConnectDataUpdateCoordinator,
        idx: tuple[int, str, str],
    ) -> None:
        """Initialize number platform for Froeling Connect integration."""
        super().__init__(coordinator, context=idx)

        self._idx = idx  # (facility_id, component_id, parameter_id)

        parameter = coordinator.data.parameters[idx]
        component = coordinator.components[idx[0]][idx[1]]
        self.parameter = parameter
        self.component = component

        self._attr_name = parameter.display_name
        self._attr_unique_id = f"{idx[0]}_{idx[1]}_{idx[2]}"
        self.entity_id = generate_entity_id(
            "number.{}",
            f"{idx[0]}_{component.display_name}_{parameter.name}",
            hass=coordinator.hass,
        )

        if parameter.unit in device_class_unit_mapping:
            cls, unit = device_class_unit_mapping[parameter.unit]
            self._attr_device_class = cls
            self._attr_native_unit_of_measurement = unit
        elif parameter.unit:
            self._attr_native_unit_of_measurement = parameter.unit

        self._attr_native_max_value = float(parameter.max_val)
        self._attr_native_min_value = float(parameter.min_val)
        self._attr_native_step = 1

        self._attr_device_info = self.coordinator.component_device_info[
            (self._idx[0], self._idx[1])
        ]

        self._attr_native_value = parameter.value

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        parameter = self.coordinator.data.parameters[self._idx]
        self._attr_native_value = parameter.value
        self.parameter = parameter

        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        LOGGER.info("New value for %s is %f", self.name, value)
        await self.parameter.set_value(str(int(value)))
