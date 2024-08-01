"""Froeling Connect coordinator."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import logging

from froeling import Component, Facility, Froeling, Parameter
from froeling.exceptions import AuthenticationError, NetworkError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LANGUAGE, CONF_PASSWORD, CONF_TOKEN, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER

type FroelingConnectConfigEntry = ConfigEntry[FroelingConnectDataUpdateCoordinator]


@dataclass
class FroelingConnectCoordinatorData:
    """Data Type of FroelingConnectDataUpdateCoordinator's data."""

    parameters: dict[tuple[int, str, str], Parameter]


class FroelingConnectDataUpdateCoordinator(
    DataUpdateCoordinator[FroelingConnectCoordinatorData]
):
    """Froeling Connect data updata coordinator."""

    config_entry: FroelingConnectConfigEntry
    froeling: Froeling

    def __init__(self, hass: HomeAssistant, name: str) -> None:
        """Initialize the Froeling Connect coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=name,
            update_interval=timedelta(seconds=60),
        )

        self.update_interval = timedelta(seconds=30)
        self.components: dict[int, dict[str, Component]] = {}
        self.data = FroelingConnectCoordinatorData({})
        self.component_device_info: dict[tuple[int, str], DeviceInfo] = {}

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        self.froeling = Froeling(
            username=self.config_entry.data[CONF_USERNAME],
            password=self.config_entry.data[CONF_PASSWORD],
            token=self.config_entry.data[CONF_TOKEN],
            auto_reauth=False,
            language=self.config_entry.data[CONF_LANGUAGE],
            logger=LOGGER,
            clientsession=async_create_clientsession(self.hass),
        )

        try:
            facilities = await self.froeling.get_facilities()
            for facility in facilities:
                self._register_facility_device_info(facility)
                components = await facility.get_components()
                for component in components:
                    self.component_device_info[
                        (component.facility_id, component.component_id)
                    ] = self._get_component_device_info(component)
                component_dict = {c.component_id: c for c in components}
                self.components[facility.facility_id] = component_dict
        except AuthenticationError as e:
            await self.froeling.session.close()
            raise ConfigEntryAuthFailed from e

        await self.async_config_entry_first_refresh()
        self._check_unregistered_parameters()

    async def _async_update_data(self) -> FroelingConnectCoordinatorData:
        """Fetch data from Froeling API."""
        try:
            async with asyncio.timeout(10):
                parameters_out = {}
                for fid, components in self.components.items():
                    for component in components.values():
                        parameters = await component.update()
                        LOGGER.debug("Pulling %s", component.display_name)
                        await asyncio.sleep(0.5)  # Ratelimit
                        for parameter in parameters:
                            parameters_out[
                                (fid, component.component_id, parameter.id)
                            ] = parameter
            return FroelingConnectCoordinatorData(parameters=parameters_out)
        except AuthenticationError as e:
            raise ConfigEntryAuthFailed from e
        except NetworkError as e:
            raise UpdateFailed from e

    def _register_facility_device_info(self, facility: Facility) -> None:
        device_registry = dr.async_get(self.hass)

        device_registry.async_get_or_create(
            config_entry_id=self.config_entry.entry_id,
            identifiers={(DOMAIN, "facility", facility.facility_id)},
            name=facility.name,
            manufacturer="Fröling",
            model=f"{facility.name} {facility.facilityGeneration}",
            model_id=facility.facility_id,
            serial_number=facility.equipmentNumber,
        )

    def _get_component_device_info(self, component: Component) -> DeviceInfo:
        return DeviceInfo(
            identifiers={
                (DOMAIN, "component", component.facility_id, component.component_id)
            },
            name=component.display_name,
            manufacturer="Fröling",
            model=component.type,
            model_id=component.sub_type,
            serial_number=component.component_id,
            via_device=(DOMAIN, "facility", component.facility_id),
        )

    def _check_unregistered_parameters(self) -> None:
        """Detect and log parameters not covered by this component."""

        def filter_sensor(param: Parameter) -> bool:
            if (
                param.parameter_type not in ("NumValueObject", "StringValueObject")
                or param.editable
            ):
                return False
            if param.min_val == "0" and param.max_val == "1" and param.unit == "":
                return False
            return True

        def filter_binary_sensor(param: Parameter) -> bool:
            if param.parameter_type != "NumValueObject" or param.editable:
                return False
            if param.min_val == "0" and param.max_val == "1" and param.unit == "":
                return True
            return False

        def filter_number(param: Parameter) -> bool:
            if param.parameter_type != "NumValueObject" or not param.editable:
                return False
            if param.min_val == "0" and param.max_val == "1" and param.unit == "":
                return False
            return True

        def filter_select(param: Parameter) -> bool:
            if (
                param.parameter_type != "StringValueObject"
                or not param.editable
                or not param.string_list_key_values
            ):
                return False
            return True

        for (_, cid, _), p in self.data.parameters.items():
            sensor = filter_sensor(p)
            binary_sensor = filter_binary_sensor(p)
            number = filter_number(p)
            select = filter_select(p)
            count = sum((sensor, binary_sensor, number, select))
            if count == 0:
                lvl = logging.DEBUG
                msg = "Parameter %s.%s.%s[%s] not registered. type: %s, editable: %s, min: %s, max: %s, unit: %s, slkv: %s"
            elif count > 1:
                lvl = logging.WARNING
                msg = f"Parameter %s.%s.%s[%s] registered multiple times {(sensor, binary_sensor, number, select)}. type: %s, editable: %s, min: %s, max: %s, unit: %s, slkv: %s"
            else:
                continue
            LOGGER.log(
                lvl,
                msg,
                p.facility_id,
                cid,
                p.id,
                p.name,
                p.parameter_type,
                p.editable,
                p.min_val,
                p.max_val,
                p.unit,
                bool(p.string_list_key_values),
            )
