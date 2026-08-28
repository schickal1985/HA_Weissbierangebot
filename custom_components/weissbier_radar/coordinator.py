"""
DataUpdateCoordinator for Weissbier Radar.
Fetches weekly deals and provides numeric prices (deal price when on promotion, regular price when not).
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
    DEFAULT_MIN_PRICE,
    DEFAULT_MAX_PRICE,
    DEFAULT_REGULAR_PRICE,
    PRODUCT_DEFINITIONS,
    STORE_DEFINITIONS,
    CONF_PRODUCTS,
    CONF_STORES,
    CONF_ZIP_CODE,
    CONF_SCAN_INTERVAL,
    CONF_MIN_PRICE,
    CONF_MAX_PRICE,
    CONF_DEAL_THRESHOLD,
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
        self.min_price = float(entry_data.get(CONF_MIN_PRICE, DEFAULT_MIN_PRICE))
        self.max_price = float(
            entry_data.get(CONF_MAX_PRICE, entry_data.get(CONF_DEAL_THRESHOLD, DEFAULT_MAX_PRICE))
        )
        self.regular_price = float(entry_data.get(CONF_REGULAR_PRICE, DEFAULT_REGULAR_PRICE))
        
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
                            "best_price": self.regular_price,
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
        regular_price = self.regular_price
        store_results: dict[str, Any] = {}

        # Initialize all known stores with regular price (No offer)
        for store_key, store_meta in STORE_DEFINITIONS.items():
            store_results[store_key] = {
                "store": store_meta["name"],
                "slug": store_key,
                "status": "Regulärer Preis (Kein Angebot)",
                "price": regular_price,
                "normalpreis": regular_price,
                "ersparnis": 0.00,
                "valid_until": None,
                "has_offer": False,
                "locations": store_meta.get("locations", ""),
                "icon": store_meta.get("icon", "mdi:store"),
            }

        found_deals: list[dict[str, Any]] = []
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

                            if price_raw and seller_name:
                                price_val = float(str(price_raw).replace(",", "."))
                                for store_key, store_meta in STORE_DEFINITIONS.items():
                                    if any(alias.lower() in seller_name.lower() for alias in store_meta.get("aliases", [])):
                                        # Filter out prices below configured min_price (e.g. single bottles < 10.00 €)
                                        if price_val < self.min_price:
                                            _LOGGER.debug(
                                                "Ignoring price %.2f € for %s at %s: Below minimum deal price %.2f € (single bottle/multipack)",
                                                price_val,
                                                prod_info["name"],
                                                seller_name,
                                                self.min_price,
                                            )
                                            rejected_single_bottle_stores.add(store_key)
                                        elif self.min_price <= price_val <= self.max_price and is_date_valid(valid_until):
                                            # Accept valid deal within [min_price, max_price]
                                            savings = max(0.0, regular_price - price_val)
                                            store_results[store_key].update({
                                                "status": "Angebot aktiv",
                                                "price": price_val,
                                                "normalpreis": regular_price,
                                                "ersparnis": round(savings, 2),
                                                "valid_until": valid_until,
                                                "has_offer": True,
                                            })
                                            found_deals.append({
                                                "store": store_meta["name"],
                                                "price": price_val,
                                                "valid_until": valid_until
                                            })

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
                                        # Only consider SaleEvent if store was not explicitly identified as single-bottle only and has no offer yet
                                        if not store_results[store_key]["has_offer"] and store_key not in rejected_single_bottle_stores:
                                            deal_p = 12.99 if "franziskaner" in prod_info["id"] else 13.99
                                            savings = max(0.0, regular_price - deal_p)
                                            store_results[store_key].update({
                                                "status": "Angebot aktiv",
                                                "price": deal_p,
                                                "normalpreis": regular_price,
                                                "ersparnis": round(savings, 2),
                                                "valid_until": end_date,
                                                "has_offer": True,
                                            })
                                            found_deals.append({
                                                "store": store_meta["name"],
                                                "price": deal_p,
                                                "valid_until": end_date
                                            })

                except Exception as err:
                    _LOGGER.debug("Error parsing LD JSON chunk: %s", err)

        # Calculate Best Price (cheapest offer if any, else regular price)
        active_offers = [s for s in store_results.values() if s.get("has_offer")]
        if active_offers:
            best_deal = min(active_offers, key=lambda x: x["price"])
            best_price = best_deal["price"]
            best_store = best_deal["store"]
            best_valid = best_deal["valid_until"]
            has_any_offer = True
            savings = best_deal["ersparnis"]
        else:
            best_price = regular_price
            best_store = "Regulärer Handel (Kein Angebot)"
            best_valid = "Dauerhaft"
            has_any_offer = False
            savings = 0.00

        return {
            "product_name": prod_info["name"],
            "best_price": best_price,
            "best_store": best_store,
            "valid_until": best_valid,
            "has_any_offer": has_any_offer,
            "normalpreis": regular_price,
            "ersparnis": savings,
            "stores": store_results,
            "url": prod_info.get("meinprospekt_url"),
        }
