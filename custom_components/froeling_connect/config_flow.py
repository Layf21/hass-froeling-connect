"""Config flow for Fröling Connect integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from froeling import Froeling
from froeling.exceptions import AuthenticationError, NetworkError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_LANGUAGE, CONF_PASSWORD, CONF_TOKEN, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, LOGGER
from .coordinator import FroelingConnectConfigEntry

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_LANGUAGE): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    try:
        api = Froeling(
            data[CONF_USERNAME], data[CONF_PASSWORD], auto_reauth=False, logger=LOGGER
        )
        userdata = await api.login()
        await api.get_facilities()
    except AuthenticationError as e:
        raise InvalidAuth from e
    except NetworkError as e:
        raise CannotConnect from e
    finally:
        await api.session.close()

    # Return info that you want to store in the config entry.
    return {
        "user_id": userdata.user_id,
        CONF_TOKEN: api.session.token,
    }


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fröling Connect."""

    VERSION = 1
    MINOR_VERSION = 0

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    user_input[CONF_USERNAME] + str(info["user_id"])
                )
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=info | user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a flow initialized by a reauth event."""

        LOGGER.info("Reauth")
        username = entry_data[CONF_USERNAME]
        password = entry_data[CONF_PASSWORD]
        entry: FroelingConnectConfigEntry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        api = Froeling(username, password, auto_reauth=False)
        await api.login()
        assert api.session.token

        await api.session.close()
        return self.async_update_reload_and_abort(
            entry,
            data={**entry.data, CONF_TOKEN: api.session.token},
            reload_even_if_entry_is_unchanged=False,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
