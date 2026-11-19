"""Read-only support for GEN_NXG components.

Uses the existing authenticated Session. No login data or tokens are stored here.
Supports the observed boiler, heating-circuit and dual-buffer API schemas.
"""
from __future__ import annotations

import math
from froeling import Component, Parameter

BASE = "https://connect-api.froeling.com/fcs/v1.0/resources/user/{}/nxg/facility/{}/web"
SUPPORTED = {"Boiler", "HeatingCircuit", "BufferTankSystemDual"}
DEFAULT_NAMES = {
    "Boiler": "Kessel", "HeatingCircuit": "Heizkreis",
    "BufferTankSystemDual": "Dual Puffersystem",
}


def walk_values(node):
    """Read all nested valueItems, without mistaking enum choices for sensors."""
    if isinstance(node, dict):
        if "type" in node and "name" in node and "value" in node:
            yield node
        for key, value in node.items():
            if key not in {"possibleValues", "value"}:
                yield from walk_values(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk_values(value)


def parse_parameters(data, session, facility_id):
    """Map NXG data to the Parameter interface used by the existing platforms."""
    result = {}
    for item in walk_values(data):
        kind = item["type"]
        name = item["name"]
        pid = str(item.get("id") or name)
        if pid in result:
            continue
        value = item.get("value")
        label = item.get("displayText") or item.get("displayFullQualifiedText")
        # Unlabelled flags describe the drawing, not user-facing measurements.
        if not label or name == "componentName":
            continue
        unit = item.get("displayUnit") or ""
        minimum = str(item["min"]) if "min" in item else None
        maximum = str(item["max"]) if "max" in item else None
        choices = None
        if kind == "BooleanValue":
            if not isinstance(value, bool):
                continue
            value = "1" if value else "0"
            parameter_type = "NumValueObject"
            minimum, maximum, unit = "0", "1", ""
        elif kind in {"NumberValue", "IntValue"}:
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                continue
            if item.get("isInvalid"):
                value = None
            parameter_type = "NumValueObject"
            # Avoid the old platform treating a numeric 0..1 value as a switch.
            if minimum == "0" and maximum == "1" and not unit:
                minimum, maximum = "0.0", "1.0"
        elif kind == "StringListValue":
            choices = {
                str(option["value"]): option.get("displayValue") or f"Wert {option['value']}"
                for option in item.get("possibleValues", []) if "value" in option
            }
            if not choices:
                continue
            value = str(value)
            if value not in choices:
                choices[value] = f"Wert {value}"
            parameter_type = "StringValueObject"
        else:
            # Text and schedules need dedicated platforms; they are not enums.
            continue
        result[pid] = NXGParameter(
            session=session, facility_id=facility_id, id=pid,
            display_name=label, name=name, editable=False,
            parameter_type=parameter_type, unit=unit, value=value,
            min_val=minimum, max_val=maximum,
            string_list_key_values=choices,
        )
    return result


class NXGParameter(Parameter):
    """NXG parameters remain read-only even if a caller invokes set_value."""

    async def set_value(self, value):
        raise NotImplementedError("Writing GEN_NXG parameters is not supported")


class NXGComponent(Component):
    """A component using the observed NXG GET endpoint."""

    def __init__(self, facility, overview):
        super().__init__(facility.facility_id, str(overview["componentId"]), facility.session)
        self.type = overview["type"]
        self.sub_type = overview.get("displayType")
        item = overview.get("valueItems", {}).get("componentName", {})
        self.display_name = item.get("value") or item.get("defaultValue") or DEFAULT_NAMES[self.type]
        self.display_category = self.type
        self.standard_name = self.display_name
        self.raw = overview

    async def update(self):
        url = BASE.format(self._session.user_id, self.facility_id)
        data = await self._session.request("get", f"{url}/component/{self.component_id}")
        if not isinstance(data, dict) or str(data.get("id")) != self.component_id:
            raise ValueError("NXG component response has an unexpected ID or format")
        parameters = parse_parameters(data, self._session, self.facility_id)
        if not parameters or not self.parameters.keys() <= parameters.keys():
            raise ValueError("NXG response is missing measurement fields; update rejected")
        self.parameters = parameters
        self.raw = data
        self.picture_url = data.get("svgUrl")
        return self.parameters


async def get_nxg_components(facility):
    url = BASE.format(facility.session.user_id, facility.facility_id)
    data = await facility.session.request("get", f"{url}/component-list")
    if not isinstance(data, list):
        raise ValueError("NXG component-list response is not a list")
    components = [NXGComponent(facility, item) for item in data
                  if item.get("type") in SUPPORTED and isinstance(item.get("componentId"), int)]
    if not components:
        raise ValueError("NXG returned no supported heating components")
    return components
