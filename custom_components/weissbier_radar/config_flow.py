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
    DEFAULT_MIN_PRICE,
    DEFAULT_MAX_PRICE,
    DEFAULT_REGULAR_PRICE,
    DEFAULT_PRODUCTS,
    DEFAULT_STORES,
    PRODUCT_DEFINITIONS,
    STORE_DEFINITIONS,
    CONF_ZIP_CODE,
    CONF_PRODUCTS,
    CONF_STORES,
    CONF_SCAN_INTERVAL,
    CONF_MIN_PRICE,
    CONF_MAX_PRICE,
    CONF_REGULAR_PRICE,
    CONF_DEAL_THRESHOLD,
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
                    CONF_MIN_PRICE, default=DEFAULT_MIN_PRICE
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0,
                        max=40.0,
                        step=0.05,
                        unit_of_measurement="€",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_MAX_PRICE, default=DEFAULT_MAX_PRICE
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0,
                        max=40.0,
                        step=0.05,
                        unit_of_measurement="€",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_REGULAR_PRICE, default=DEFAULT_REGULAR_PRICE
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0,
                        max=40.0,
                        step=0.05,
                        unit_of_measurement="€",
                        mode=selector.NumberSelectorMode.BOX,
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

    def __init__(self, config_entry: config_entries.ConfigEntry | None = None) -> None:
        """Initialize options flow."""
        if config_entry is not None:
            self._config_entry = config_entry

    @property
    def config_entry(self) -> config_entries.ConfigEntry:
        """Return config entry."""
        return self._config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Merge data and options to retrieve currently configured values
        current_config = {**self.config_entry.data, **self.config_entry.options}

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ZIP_CODE,
                    default=current_config.get(CONF_ZIP_CODE, DEFAULT_ZIP_CODE),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(
                    CONF_PRODUCTS,
                    default=current_config.get(CONF_PRODUCTS, DEFAULT_PRODUCTS),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=PRODUCT_OPTIONS,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_STORES,
                    default=current_config.get(CONF_STORES, DEFAULT_STORES),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=STORE_OPTIONS,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_MIN_PRICE,
                    default=float(current_config.get(CONF_MIN_PRICE, DEFAULT_MIN_PRICE)),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0,
                        max=40.0,
                        step=0.05,
                        unit_of_measurement="€",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_MAX_PRICE,
                    default=float(
                        current_config.get(
                            CONF_MAX_PRICE,
                            current_config.get(CONF_DEAL_THRESHOLD, DEFAULT_MAX_PRICE),
                        )
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0,
                        max=40.0,
                        step=0.05,
                        unit_of_measurement="€",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_REGULAR_PRICE,
                    default=float(current_config.get(CONF_REGULAR_PRICE, DEFAULT_REGULAR_PRICE)),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0,
                        max=40.0,
                        step=0.05,
                        unit_of_measurement="€",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=current_config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS),
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
