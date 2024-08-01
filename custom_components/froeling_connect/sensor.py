"""Platform for Fröling Connect integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION
from .coordinator import (
    FroelingConnectConfigEntry,
    FroelingConnectDataUpdateCoordinator,
)

device_class_unit_mapping: dict[str, str] = {
    "°C": (SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS),
    "°F": (SensorDeviceClass.TEMPERATURE, UnitOfTemperature.FAHRENHEIT),
    "h": (SensorDeviceClass.DURATION, UnitOfTime.HOURS),
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
        if (
            param.parameter_type not in ("NumValueObject", "StringValueObject")
            or param.editable
        ):
            continue
        if param.min_val == "0" and param.max_val == "1" and param.unit == "":
            continue
        entities.append(FroelingConnectSensor(coordinator, idx))

    async_add_entities(entities)


class FroelingConnectSensor(
    CoordinatorEntity[FroelingConnectDataUpdateCoordinator], SensorEntity
):
    """Representation of a Sensor."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FroelingConnectDataUpdateCoordinator,
        idx: tuple[int, str, str],
    ) -> None:
        """Initialize temperature sensor for Froeling Connect integration."""
        super().__init__(coordinator, context=idx)

        self._idx = idx  # (facility_id, component_id, parameter_id)

        parameter = coordinator.data.parameters[idx]
        component = coordinator.components[idx[0]][idx[1]]
        self.parameter = parameter
        self.component = component

        self._attr_name = parameter.display_name
        self._attr_unique_id = f"{idx[0]}_{idx[1]}_{idx[2]}"
        self.entity_id = generate_entity_id(
            "sensor.{}",
            f"{idx[0]}_{component.display_name}_{parameter.name}",
            hass=coordinator.hass,
        )

        if parameter.parameter_type == "NumValueObject":
            self._attr_suggested_display_precision = 0
            if parameter.unit in device_class_unit_mapping:
                cls, unit = device_class_unit_mapping[parameter.unit]
                self._attr_device_class = cls
                self._attr_native_unit_of_measurement = unit
            elif parameter.unit:
                self._attr_native_unit_of_measurement = parameter.unit
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif parameter.parameter_type == "StringValueObject":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = list(parameter.string_list_key_values.values())

        self._attr_device_info = self.coordinator.component_device_info[
            (self._idx[0], self._idx[1])
        ]

        self._set_value()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._set_value()
        self.async_write_ha_state()

    def _set_value(self) -> None:
        parameter = self.coordinator.data.parameters[self._idx]

        if (
            parameter.string_list_key_values
            and str(parameter.value) in parameter.string_list_key_values
        ):
            self._attr_native_value = parameter.string_list_key_values[
                str(parameter.value)
            ]
        else:
            self._attr_native_value = parameter.value
