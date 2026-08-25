"""
Config Flow for Weissbier Radar integration.
Allows UI-based configuration of PLZ, products, stores, and update intervals.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    NAME,
    DEFAULT_ZIP_CODE,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DEFAULT_PRODUCTS,
    DEFAULT_STORES,
    PRODUCT_DEFINITIONS,
    STORE_DEFINITIONS,
    CONF_ZIP_CODE,
    CONF_PRODUCTS,
    CONF_STORES,
    CONF_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PRODUCT_OPTIONS = [
    selector.SelectOptionDict(value=k, label=v["name"])
    for k, v in PRODUCT_DEFINITIONS.items()
]

STORE_OPTIONS = [
    selector.SelectOptionDict(value=k, label=v["name"])
    for k, v in STORE_DEFINITIONS.items()
]

class WeissbierRadarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Weissbier Radar."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Prevent duplicate entries for the same ZIP code
            await self.async_set_unique_id(f"weissbier_radar_{user_input[CONF_ZIP_CODE]}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Weissbier Radar ({user_input[CONF_ZIP_CODE]})",
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_ZIP_CODE, default=DEFAULT_ZIP_CODE): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(
                    CONF_PRODUCTS, default=DEFAULT_PRODUCTS
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=PRODUCT_OPTIONS,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_STORES, default=DEFAULT_STORES
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=STORE_OPTIONS,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL_HOURS
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=24,
                        unit_of_measurement="Stunden",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return WeissbierRadarOptionsFlowHandler(config_entry)


class WeissbierRadarOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Weissbier Radar."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ZIP_CODE,
                    default=self.config_entry.data.get(CONF_ZIP_CODE, DEFAULT_ZIP_CODE),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(
                    CONF_PRODUCTS,
                    default=self.config_entry.data.get(CONF_PRODUCTS, DEFAULT_PRODUCTS),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=PRODUCT_OPTIONS,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_STORES,
                    default=self.config_entry.data.get(CONF_STORES, DEFAULT_STORES),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=STORE_OPTIONS,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=24,
                        unit_of_measurement="Stunden",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
