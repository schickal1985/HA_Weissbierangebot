"""
==============================================================================
🍺 WEISSBIER-RADAR - Multi-Source Angebotssuche für Franziskaner & Erdinger
Quellen: MeinProspekt, KaufDA & Aktionspreis (Bonial & Aggregatoren)
Region: PLZ 84385 (Pfarrkirchen, Aidenbach, Bad Birnbach)
==============================================================================
"""

import urllib.request
import re
import json
import sys
import os
from bs4 import BeautifulSoup

# UTF-8 Support for Windows Console
if sys.platform == "win32":
    os.system("chcp 65001 >nul")
    sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
}

PRODUCTS = [
    {
        "id": "franziskaner",
        "name": "Franziskaner Weißbier (20 x 0,5l Kasten)",
        "slug": "franziskaner",
        "aktionspreis_url": "https://www.aktionspreis.de/angebote/franziskaner-kasten-20-x-0-5l",
        "meinprospekt_url": "https://www.meinprospekt.de/angebote/franziskaner",
        "kaufda_url": "https://www.kaufda.de/Angebote/Franziskaner",
        "icon": "🍺"
    },
    {
        "id": "erdinger",
        "name": "Erdinger Weißbier (20 x 0,5l Kasten)",
        "slug": "erdinger",
        "aktionspreis_url": "https://www.aktionspreis.de/angebote/erdinger-kasten-20-x-0-5l",
        "meinprospekt_url": "https://www.meinprospekt.de/angebote/erdinger",
        "kaufda_url": "https://www.kaufda.de/Angebote/Erdinger",
        "icon": "🍻"
    }
]

TARGET_STORES = [
    {
        "key": "netto-marken-discount",
        "name": "Netto Marken-Discount",
        "aliases": ["Netto Marken-Discount", "Netto"],
        "locations": "Aidenbach, Pfarrkirchen"
    },
    {
        "key": "edeka",
        "name": "Edeka",
        "aliases": ["Edeka", "EDEKA", "Edeka Center"],
        "locations": "Pfarrkirchen, Aidenbach, Bad Birnbach"
    },
    {
        "key": "kaufland",
        "name": "Kaufland",
        "aliases": ["Kaufland"],
        "locations": "Pfarrkirchen"
    }
]

def fetch_html(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return ""

def parse_bonial_sources(p: dict) -> dict:
    """Parses MeinProspekt and KaufDA JSON-LD schemas."""
    store_deals = {}
    
    for url in [p["meinprospekt_url"], p["kaufda_url"]]:
        html = fetch_html(url)
        if not html:
            continue
            
        soup = BeautifulSoup(html, "html.parser")
        
        # 1. Check Schema.org Offer / AggregateOffer / Product
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(s.get_text())
                
                # Check AggregateOffer / Offer with Seller
                if isinstance(data, dict):
                    # Direct offers list
                    offers_list = data.get("offers", [])
                    if isinstance(offers_list, dict):
                        offers_list = [offers_list]
                        
                    for off in offers_list:
                        # Sometimes nested in itemOffered
                        item = off.get("itemOffered", {}) if isinstance(off, dict) else {}
                        nested_offers = item.get("offers", {}) if isinstance(item, dict) else {}
                        
                        target_off = nested_offers if nested_offers else off
                        if isinstance(target_off, dict):
                            price = target_off.get("price") or target_off.get("lowPrice")
                            valid_until = target_off.get("priceValidUntil")
                            seller = target_off.get("seller", {}) or target_off.get("manufacturer", {})
                            seller_name = seller.get("name", "") if isinstance(seller, dict) else str(seller)
                            
                            if price and seller_name:
                                for store in TARGET_STORES:
                                    if any(alias.lower() in seller_name.lower() for alias in store["aliases"]):
                                        store_deals[store["key"]] = {
                                            "name": store["name"],
                                            "location": store["locations"],
                                            "price": float(str(price).replace(",", ".")),
                                            "valid": valid_until,
                                            "active": True,
                                            "source": "MeinProspekt/KaufDA"
                                        }

                    # Check OfferCatalog SaleEvents
                    items = data.get("itemListElement", [])
                    for item in items:
                        if isinstance(item, dict) and item.get("@type") == "SaleEvent":
                            event_name = item.get("name", "")
                            end_date = item.get("endDate", "")
                            performer = item.get("performer", {})
                            p_name = performer.get("name", "") if isinstance(performer, dict) else str(performer)
                            
                            for store in TARGET_STORES:
                                if any(alias.lower() in event_name.lower() or alias.lower() in p_name.lower() for alias in store["aliases"]):
                                    if store["key"] not in store_deals:
                                        # If price was in product schema
                                        prod_schema = soup.find("script", string=re.compile(r'"@type":\s*"Product"'))
                                        p_val = None
                                        if prod_schema:
                                            p_data = json.loads(prod_schema.get_text())
                                            p_off = p_data.get("offers", {})
                                            if p_off.get("lowPrice") or p_off.get("price"):
                                                p_val = float(str(p_off.get("lowPrice") or p_off.get("price")).replace(",", "."))
                                        
                                        store_deals[store["key"]] = {
                                            "name": store["name"],
                                            "location": store["locations"],
                                            "price": p_val or 12.99,
                                            "valid": end_date,
                                            "active": True,
                                            "source": "KaufDA"
                                        }
            except Exception:
                pass
                
    return store_deals

def check_deals():
    print("=" * 72)
    print(" 🍺 WEISSBIER-RADAR - AKTUELLE PROSPEKT-ANGEBOTE")
    print(" Region: PLZ 84385 (Pfarrkirchen, Aidenbach, Bad Birnbach)")
    print("=" * 72)

    for p in PRODUCTS:
        print(f"\n{p['icon']}  {p['name']}")
        print("-" * 72)

        # Multi-Source parsing
        deals = parse_bonial_sources(p)

        # Find best price
        active_prices = [d["price"] for d in deals.values() if d.get("price")]
        if active_prices:
            best_p = min(active_prices)
            print(f"  ⭐ Bester lokaler Angebotspreis: \033[1m\033[93m{best_p:.2f} €\033[0m")
        else:
            print("  ⭐ Bester lokaler Angebotspreis: Aktuell kein Werbepreis gefunden")

        print("\n  Deine lokalen Filialen:")
        for target in TARGET_STORES:
            offer = deals.get(target["key"])
            if offer and offer["active"] and offer["price"]:
                valid_str = f"bis {offer['valid']}" if offer['valid'] else "diese Woche"
                print(f"    ✅ \033[92m{target['name']:<24}\033[0m: \033[1m\033[93m{offer['price']:.2f} €\033[0m (Gültig {valid_str}) [{target['locations']}]")
            else:
                print(f"    ❌ {target['name']:<24}: Kein Angebot aktiv [{target['locations']}]")

    print("\n" + "=" * 72)
    print(" Abfrage abgeschlossen. Zum Beenden beliebige Taste drücken...")
    print("=" * 72)

if __name__ == "__main__":
    check_deals()
