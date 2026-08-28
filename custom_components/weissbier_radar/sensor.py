"""
Sensor platform for Weissbier Radar integration.
Provides numeric price sensors with offer tracking and regular pricing fallbacks.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    PRODUCT_DEFINITIONS,
    STORE_DEFINITIONS,
    CONF_PRODUCTS,
    CONF_STORES,
)
from .coordinator import WeissbierRadarDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform from a config entry."""
    coordinator: WeissbierRadarDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    config_data = {**entry.data, **entry.options}
    selected_products = config_data.get(CONF_PRODUCTS, list(PRODUCT_DEFINITIONS.keys()))
    selected_stores = config_data.get(CONF_STORES, list(STORE_DEFINITIONS.keys()))

    for prod_id in selected_products:
        if prod_id not in PRODUCT_DEFINITIONS:
            continue
        
        # 1. Add Best Price Sensor for this product
        entities.append(
            WeissbierBestPriceSensor(coordinator, entry, prod_id)
        )

        # 2. Add Individual Store Sensors for this product
        for store_id in selected_stores:
            if store_id not in STORE_DEFINITIONS:
                continue
            entities.append(
                WeissbierStoreSensor(coordinator, entry, prod_id, store_id)
            )

    async_add_entities(entities)


class WeissbierBaseSensor(CoordinatorEntity[WeissbierRadarDataUpdateCoordinator], SensorEntity):
    """Base sensor for Weissbier Radar."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "€"
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: WeissbierRadarDataUpdateCoordinator,
        entry: ConfigEntry,
        prod_id: str,
    ) -> None:
        """Initialize the base sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self.prod_id = prod_id
        self.prod_info = PRODUCT_DEFINITIONS[prod_id]

    @property
    def product_data(self) -> dict[str, Any]:
        """Return the current product data from coordinator."""
        if not self.coordinator.data or self.prod_id not in self.coordinator.data:
            return {}
        return self.coordinator.data[self.prod_id]


class WeissbierBestPriceSensor(WeissbierBaseSensor):
    """Sensor showing lowest price (deal or regular) across all stores for a product."""

    def __init__(
        self,
        coordinator: WeissbierRadarDataUpdateCoordinator,
        entry: ConfigEntry,
        prod_id: str,
    ) -> None:
        """Initialize the best price sensor."""
        super().__init__(coordinator, entry, prod_id)
        self._attr_unique_id = f"{entry.entry_id}_{prod_id}_bester_preis"
        self._attr_name = f"{self.prod_info['name']} Bester Preis"
        self._attr_icon = "mdi:tag-heart"

    @property
    def native_value(self) -> float | None:
        """Return the lowest available price as numeric float."""
        data = self.product_data
        best_price = data.get("best_price")
        if best_price is not None:
            return float(best_price)
        return float(self.prod_info.get("regular_price", 20.49))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        data = self.product_data
        has_offer = data.get("has_any_offer", False)
        
        return {
            "produkt": self.prod_info["name"],
            "im_angebot": has_offer,
            "status": "Angebot aktiv" if has_offer else "Regulärer Preis (Kein Angebot)",
            "normalpreis": f"{data.get('normalpreis', 20.49):.2f} €",
            "ersparnis": f"{data.get('ersparnis', 0.0):.2f} €",
            "bester_haendler": data.get("best_store", "Regulärer Handel"),
            "gueltig_bis": data.get("valid_until", "Dauerhaft"),
            "angebots_link": self.prod_info.get("meinprospekt_url"),
            "plz": self.coordinator.zip_code,
            "gebinde": "Kasten 20 x 0,5l",
        }


class WeissbierStoreSensor(WeissbierBaseSensor):
    """Sensor showing product deal or regular price for a specific store."""

    def __init__(
        self,
        coordinator: WeissbierRadarDataUpdateCoordinator,
        entry: ConfigEntry,
        prod_id: str,
        store_id: str,
    ) -> None:
        """Initialize the store deal sensor."""
        super().__init__(coordinator, entry, prod_id)
        self.store_id = store_id
        self.store_info = STORE_DEFINITIONS[store_id]
        
        self._attr_unique_id = f"{entry.entry_id}_{prod_id}_{store_id}"
        self._attr_name = f"{self.prod_info['name']} {self.store_info['name']}"
        self._attr_icon = self.store_info.get("icon", "mdi:store")

    @property
    def native_value(self) -> float | None:
        """Return the current store price (deal price or regular price)."""
        data = self.product_data
        store_data = data.get("stores", {}).get(self.store_id, {})
        
        price = store_data.get("price")
        if price is not None:
            return float(price)
        return float(self.prod_info.get("regular_price", 20.49))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes for store deal."""
        data = self.product_data
        store_data = data.get("stores", {}).get(self.store_id, {})
        
        has_offer = store_data.get("has_offer", False)
        return {
            "haendler": self.store_info["name"],
            "produkt": self.prod_info["name"],
            "im_angebot": has_offer,
            "status": "Angebot aktiv" if has_offer else "Regulärer Preis (Kein Angebot)",
            "normalpreis": f"{store_data.get('normalpreis', 20.49):.2f} €",
            "ersparnis": f"{store_data.get('ersparnis', 0.0):.2f} €",
            "gueltig_bis": store_data.get("valid_until") or "Dauerhaft",
            "filialen": store_data.get("locations", ""),
            "gebinde": "Kasten 20 x 0,5l",
            "plz": self.coordinator.zip_code,
            "angebots_link": self.prod_info.get("meinprospekt_url"),
        }
