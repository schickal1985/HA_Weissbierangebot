"""
DataUpdateCoordinator for Weissbier Radar.
Fetches weekly deals and provides numeric prices (> 8.00 €) for beer crates.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any

from bs4 import BeautifulSoup
import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL_HOURS,
    MIN_CRATE_PRICE,
    DEFAULT_FALLBACK_PRICE,
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

def is_date_valid(valid_until_str: str | None) -> bool:
    """Check if the date string is still valid today or in the future."""
    if not valid_until_str:
        return True  # If no date is given, assume current week
    try:
        # Check ISO format YYYY-MM-DD
        if "-" in valid_until_str:
            d = datetime.strptime(valid_until_str[:10], "%Y-%m-%d").date()
            return d >= date.today()
        # Check German format DD.MM.YYYY or DD.MM.YY
        if "." in valid_until_str:
            parts = valid_until_str.strip().split(".")
            if len(parts) >= 3:
                year = int(parts[2])
                if year < 100:
                    year += 2000
                d = date(year, int(parts[1]), int(parts[0]))
                return d >= date.today()
    except Exception:
        pass
    return True

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
        """Fetch data from deal engines."""
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
                            "best_price": DEFAULT_FALLBACK_PRICE,
                            "valid_until": None,
                            "has_any_offer": False,
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
            prod_info.get("aktionspreis_url"),
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
        all_found_prices: list[float] = []
        specific_store_deals: dict[str, dict[str, Any]] = {}
        rejected_single_bottle_stores: set[str] = set()

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

                            if price_raw:
                                price_val = float(str(price_raw).replace(",", "."))
                                
                                # Filter out single bottles / small packs (<= MIN_CRATE_PRICE 8.00 €)
                                if price_val <= MIN_CRATE_PRICE:
                                    if seller_name:
                                        for store_key, store_meta in STORE_DEFINITIONS.items():
                                            if any(alias.lower() in seller_name.lower() for alias in store_meta.get("aliases", [])):
                                                rejected_single_bottle_stores.add(store_key)
                                    continue

                                # Valid crate price (> 8.00 €)
                                if is_date_valid(valid_until):
                                    all_found_prices.append(price_val)
                                    if seller_name:
                                        for store_key, store_meta in STORE_DEFINITIONS.items():
                                            if any(alias.lower() in seller_name.lower() for alias in store_meta.get("aliases", [])):
                                                if store_key not in specific_store_deals or price_val < specific_store_deals[store_key]["price"]:
                                                    specific_store_deals[store_key] = {
                                                        "price": price_val,
                                                        "valid_until": valid_until,
                                                        "store": store_meta["name"],
                                                    }

                    # 2. OfferCatalog SaleEvents
                    items = data.get("itemListElement", [])
                    for item in items:
                        if isinstance(item, dict) and item.get("@type") == "SaleEvent":
                            event_name = item.get("name", "")
                            end_date = item.get("endDate", "")
                            performer = item.get("performer", {})
                            p_name = performer.get("name", "") if isinstance(performer, dict) else str(performer)

                            if is_date_valid(end_date):
                                for store_key, store_meta in STORE_DEFINITIONS.items():
                                    if any(alias.lower() in event_name.lower() or alias.lower() in p_name.lower() for alias in store_meta.get("aliases", [])):
                                        if store_key not in specific_store_deals and store_key not in rejected_single_bottle_stores:
                                            deal_p = 12.99 if "franziskaner" in prod_info["id"] else 13.99
                                            all_found_prices.append(deal_p)
                                            specific_store_deals[store_key] = {
                                                "price": deal_p,
                                                "valid_until": end_date,
                                                "store": store_meta["name"],
                                            }

                except Exception as err:
                    _LOGGER.debug("Error parsing LD JSON chunk: %s", err)

        # Highest price found is used as regular price (or default fallback)
        highest_price = max(all_found_prices) if all_found_prices else DEFAULT_FALLBACK_PRICE
        highest_price = max(highest_price, DEFAULT_FALLBACK_PRICE)

        # Build results for all configured stores
        store_results: dict[str, Any] = {}
        for store_key, store_meta in STORE_DEFINITIONS.items():
            if store_key in specific_store_deals:
                p = specific_store_deals[store_key]["price"]
                has_offer = (p < highest_price)
                store_results[store_key] = {
                    "store": store_meta["name"],
                    "slug": store_key,
                    "status": "Angebot aktiv" if has_offer else "Regulärer Preis (Kein Angebot)",
                    "price": p,
                    "normalpreis": highest_price,
                    "valid_until": specific_store_deals[store_key]["valid_until"] or "Dauerhaft",
                    "has_offer": has_offer,
                    "locations": store_meta.get("locations", ""),
                    "icon": store_meta.get("icon", "mdi:store"),
                }
            else:
                # Stores without leaflet entry take the highest found price
                store_results[store_key] = {
                    "store": store_meta["name"],
                    "slug": store_key,
                    "status": "Regulärer Preis (Kein Angebot)",
                    "price": highest_price,
                    "normalpreis": highest_price,
                    "valid_until": "Dauerhaft",
                    "has_offer": False,
                    "locations": store_meta.get("locations", ""),
                    "icon": store_meta.get("icon", "mdi:store"),
                }

        # Calculate Best Price (lowest price across all stores)
        best_deal = min(store_results.values(), key=lambda x: x["price"])
        best_price = best_deal["price"]
        best_store = best_deal["store"]
        best_valid = best_deal["valid_until"]
        has_any_offer = (best_price < highest_price)

        return {
            "product_name": prod_info["name"],
            "best_price": best_price,
            "best_store": best_store,
            "valid_until": best_valid,
            "has_any_offer": has_any_offer,
            "normalpreis": highest_price,
            "stores": store_results,
            "url": prod_info.get("meinprospekt_url"),
        }
