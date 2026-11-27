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

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_LANGUAGE, default="en"): str,
        vol.Required(CONF_SEND_CHANGES, default=True): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: Mapping[str, Any]) -> dict[str, Any]:
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

    async def _async_try_login(
        self, data: Mapping[str, Any]
    ) -> tuple[dict[str, Any] | None, dict[str, str]]:
        """Validate credentials and map exceptions to form errors."""
        errors: dict[str, str] = {}
        try:
            info = await validate_input(self.hass, data)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # noqa: BLE001
            LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return info, errors
        return None, errors

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            info, errors = await self._async_try_login(user_input)
            if info is not None:
                await self.async_set_unique_id(str(info["user_id"]))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=info | user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by a reauth event.

        First try to refresh the token with the stored credentials. If that
        fails, ask the user for a new password.
        """
        LOGGER.info("Reauth")
        entry = self._get_reauth_entry()

        info, _ = await self._async_try_login(entry_data)
        if info is not None:
            return self.async_update_reload_and_abort(
                entry,
                data={**entry.data, CONF_TOKEN: info[CONF_TOKEN]},
                reload_even_if_entry_is_unchanged=False,
            )

        LOGGER.info("Stored credentials are no longer valid, asking user to reauthenticate")
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Ask the user for a new password during reauth."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
            info, errors = await self._async_try_login(data)
            if info is not None:
                await self.async_set_unique_id(str(info["user_id"]))
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry, data={**data, CONF_TOKEN: info[CONF_TOKEN]}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={CONF_USERNAME: entry.data[CONF_USERNAME]},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle a reconfiguration flow initialized by the user.

        Allows changing the login credentials, the language and the
        ``send_changes`` option. The new credentials are validated against the
        API before they are stored, and a fresh token is saved.
        """
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            info, errors = await self._async_try_login(user_input)
            if info is not None:
                await self.async_set_unique_id(str(info["user_id"]))
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    title=user_input[CONF_USERNAME],
                    data={**entry.data, **user_input, **info},
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=entry.data[CONF_USERNAME]): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(
                        CONF_LANGUAGE, default=entry.data.get(CONF_LANGUAGE, "en")
                    ): str,
                    vol.Required(
                        CONF_SEND_CHANGES,
                        default=entry.data.get(CONF_SEND_CHANGES, True),
                    ): bool,
                }
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
