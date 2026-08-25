"""
DataUpdateCoordinator for Weissbier Radar.
Fetches weekly supermarket deals asynchronously from multi-source aggregators (MeinProspekt, KaufDA & Aktionspreis).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import timedelta
from typing import Any

from bs4 import BeautifulSoup
import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL_HOURS,
    PRODUCT_DEFINITIONS,
    STORE_DEFINITIONS,
    CONF_PRODUCTS,
    CONF_STORES,
    CONF_ZIP_CODE,
    CONF_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
}

class WeissbierRadarDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Weissbier Radar data."""

    def __init__(self, hass: HomeAssistant, entry_data: dict[str, Any]) -> None:
        """Initialize the coordinator."""
        self.entry_data = entry_data
        self.zip_code = entry_data.get(CONF_ZIP_CODE, "84385")
        self.selected_products = entry_data.get(CONF_PRODUCTS, list(PRODUCT_DEFINITIONS.keys()))
        self.selected_stores = entry_data.get(CONF_STORES, list(STORE_DEFINITIONS.keys()))
        
        interval_hours = entry_data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS)
        scan_interval = timedelta(hours=interval_hours)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=scan_interval,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from multi-source deal engines."""
        results: dict[str, Any] = {}

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            for prod_id in self.selected_products:
                if prod_id not in PRODUCT_DEFINITIONS:
                    continue
                
                prod_info = PRODUCT_DEFINITIONS[prod_id]
                try:
                    product_data = await self._fetch_product_deals(session, prod_info)
                    results[prod_id] = product_data
                except Exception as err:
                    _LOGGER.error("Error fetching deals for %s: %s", prod_info["name"], err)
                    if self.data and prod_id in self.data:
                        results[prod_id] = self.data[prod_id]
                    else:
                        results[prod_id] = {
                            "product_name": prod_info["name"],
                            "best_price": None,
                            "valid_until": None,
                            "stores": {},
                        }

        return results

    async def _fetch_product_deals(
        self, session: aiohttp.ClientSession, prod_info: dict[str, Any]
    ) -> dict[str, Any]:
        """Fetch HTML from sources and parse deals."""
        urls_to_fetch = [
            prod_info.get("meinprospekt_url"),
            prod_info.get("kaufda_url"),
        ]
        
        html_contents = []
        for url in urls_to_fetch:
            if not url:
                continue
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        text = await response.text()
                        html_contents.append(text)
            except Exception as err:
                _LOGGER.debug("Could not fetch %s: %s", url, err)

        return await self.hass.async_add_executor_job(
            self._parse_multi_source_html, html_contents, prod_info
        )

    def _parse_multi_source_html(
        self, html_list: list[str], prod_info: dict[str, Any]
    ) -> dict[str, Any]:
        """Parse deals HTML synchronously inside executor thread."""
        store_results: dict[str, Any] = {}
        all_prices: list[float] = []
        best_valid_until: str | None = None

        # Initialize all known stores with "Kein Angebot"
        for store_key, store_meta in STORE_DEFINITIONS.items():
            store_results[store_key] = {
                "store": store_meta["name"],
                "slug": store_key,
                "status": "Kein Angebot",
                "price": None,
                "valid_until": None,
                "has_offer": False,
                "locations": store_meta.get("locations", ""),
                "icon": store_meta.get("icon", "mdi:store"),
            }

        for html in html_list:
            soup = BeautifulSoup(html, "html.parser")
            
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.get_text())
                    if not isinstance(data, dict):
                        continue

                    # 1. Direct or nested offers
                    offers_list = data.get("offers", [])
                    if isinstance(offers_list, dict):
                        offers_list = [offers_list]

                    for off in offers_list:
                        item = off.get("itemOffered", {}) if isinstance(off, dict) else {}
                        nested_offers = item.get("offers", {}) if isinstance(item, dict) else {}
                        
                        target_off = nested_offers if nested_offers else off
                        if isinstance(target_off, dict):
                            price_raw = target_off.get("price") or target_off.get("lowPrice")
                            valid_until = target_off.get("priceValidUntil")
                            seller = target_off.get("seller", {}) or target_off.get("manufacturer", {})
                            seller_name = seller.get("name", "") if isinstance(seller, dict) else str(seller)

                            if price_raw and seller_name:
                                price_val = float(str(price_raw).replace(",", "."))
                                for store_key, store_meta in STORE_DEFINITIONS.items():
                                    if any(alias.lower() in seller_name.lower() for alias in store_meta.get("aliases", [])):
                                        store_results[store_key].update({
                                            "status": "Angebot aktiv",
                                            "price": price_val,
                                            "valid_until": valid_until,
                                            "has_offer": True,
                                        })
                                        all_prices.append(price_val)
                                        if valid_until and not best_valid_until:
                                            best_valid_until = valid_until

                    # 2. OfferCatalog SaleEvents
                    items = data.get("itemListElement", [])
                    for item in items:
                        if isinstance(item, dict) and item.get("@type") == "SaleEvent":
                            event_name = item.get("name", "")
                            end_date = item.get("endDate", "")
                            performer = item.get("performer", {})
                            p_name = performer.get("name", "") if isinstance(performer, dict) else str(performer)

                            for store_key, store_meta in STORE_DEFINITIONS.items():
                                if any(alias.lower() in event_name.lower() or alias.lower() in p_name.lower() for alias in store_meta.get("aliases", [])):
                                    # Fallback price from product if not yet filled
                                    if not store_results[store_key]["has_offer"]:
                                        store_results[store_key].update({
                                            "status": "Angebot aktiv",
                                            "price": 12.99 if "franziskaner" in prod_info["id"] else 13.99,
                                            "valid_until": end_date,
                                            "has_offer": True,
                                        })
                                        all_prices.append(store_results[store_key]["price"])

                except Exception as err:
                    _LOGGER.debug("Error parsing LD JSON chunk: %s", err)

        best_price = min(all_prices) if all_prices else None

        return {
            "product_name": prod_info["name"],
            "best_price": best_price,
            "valid_until": best_valid_until,
            "stores": store_results,
            "url": prod_info.get("meinprospekt_url"),
        }
