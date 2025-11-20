"""Config flow for Fröling Connect integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from froeling import Froeling
from froeling.exceptions import AuthenticationError, NetworkError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_LANGUAGE, CONF_PASSWORD, CONF_TOKEN, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import CONF_SEND_CHANGES, DOMAIN, LOGGER
from .coordinator import FroelingConnectConfigEntry

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_LANGUAGE, default="en"): str,
        vol.Required(CONF_SEND_CHANGES, default=True): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    try:
        api = Froeling(
            data[CONF_USERNAME],
            data[CONF_PASSWORD],
            auto_reauth=False,
            logger=LOGGER,
            clientsession=async_create_clientsession(hass),
        )
        userdata = await api.login()
        await api.get_facilities()
    except AuthenticationError as e:
        raise InvalidAuth from e
    except NetworkError as e:
        raise CannotConnect from e

    # Return info that you want to store in the config entry.
    return {
        "user_id": userdata.user_id,
        CONF_TOKEN: api.session.token,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fröling Connect."""

    VERSION = 1
    MINOR_VERSION = 0

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(str(info["user_id"]))
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=info | user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by a reauth event."""

        LOGGER.info("Reauth")
        username = entry_data[CONF_USERNAME]
        password = entry_data[CONF_PASSWORD]
        entry: FroelingConnectConfigEntry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        api = Froeling(
            username,
            password,
            auto_reauth=False,
            clientsession=async_create_clientsession(self.hass),
        )
        await api.login()
        assert api.session.token

        return self.async_update_reload_and_abort(
            entry,
            data={**entry.data, CONF_TOKEN: api.session.token},
            reload_even_if_entry_is_unchanged=False,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle a reconfiguration flow initialized by the user."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                entry,
                data=entry.data | {CONF_SEND_CHANGES: user_input[CONF_SEND_CHANGES]},
            )
            await self.hass.config_entries.async_reload(entry.entry_id)
            return self.async_abort(reason="reconfigure_successful")

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SEND_CHANGES, default=entry.data[CONF_SEND_CHANGES]
                    ): bool
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
