"""
Sensor platform for Weissbier Radar integration.
Provides read-only sensors for beer prices and offers.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
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

    selected_products = entry.data.get(CONF_PRODUCTS, list(PRODUCT_DEFINITIONS.keys()))
    selected_stores = entry.data.get(CONF_STORES, list(STORE_DEFINITIONS.keys()))

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
    """Sensor showing the lowest active price across all stores for a product."""

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
        self._attr_native_unit_of_measurement = "€"
        self._attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float | str | None:
        """Return the lowest available price."""
        data = self.product_data
        best_price = data.get("best_price")
        if best_price is not None:
            return float(best_price)
        return "Kein Angebot"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        data = self.product_data
        stores = data.get("stores", {})
        
        # Find store with the best price
        best_store = "Unbekannt"
        valid_until = data.get("valid_until")
        
        active_stores = [s for s in stores.values() if s.get("has_offer") and s.get("price")]
        if active_stores:
            cheapest = min(active_stores, key=lambda x: x["price"])
            best_store = cheapest.get("store", "Unbekannt")
            valid_until = cheapest.get("valid_until", valid_until)

        return {
            "produkt": self.prod_info["name"],
            "bester_haendler": best_store,
            "gueltig_bis": valid_until,
            "angebots_link": self.prod_info.get("url"),
            "plz": self.coordinator.zip_code,
            "gebinde": "Kasten 20 x 0,5l",
        }


class WeissbierStoreSensor(WeissbierBaseSensor):
    """Sensor showing product deal status for a specific store."""

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
        self._attr_native_unit_of_measurement = "€"
        self._attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float | str | None:
        """Return the current store price or status."""
        data = self.product_data
        store_data = data.get("stores", {}).get(self.store_id, {})
        
        if store_data.get("has_offer") and store_data.get("price") is not None:
            return float(store_data["price"])
        return "Kein Angebot"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes for store deal."""
        data = self.product_data
        store_data = data.get("stores", {}).get(self.store_id, {})
        
        has_offer = store_data.get("has_offer", False)
        return {
            "haendler": self.store_info["name"],
            "produkt": self.prod_info["name"],
            "angebot_aktiv": has_offer,
            "gueltig_bis": store_data.get("valid_until"),
            "gebinde": "Kasten 20 x 0,5l",
            "plz": self.coordinator.zip_code,
            "angebots_link": self.prod_info.get("url"),
        }
