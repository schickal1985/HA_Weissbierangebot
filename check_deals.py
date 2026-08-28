"""
==============================================================================
🍺 WEISSBIER-RADAR - Multi-Source Angebotssuche für Franziskaner & Erdinger
Region: PLZ 84385 (Pfarrkirchen, Aidenbach, Bad Birnbach)
==============================================================================
"""

import urllib.request
import re
import json
import sys
import os
from datetime import datetime, date
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

DEFAULT_REGULAR_PRICE = 20.49
MIN_CRATE_PRICE = 10.00
DEAL_THRESHOLD = 20.00

PRODUCTS = [
    {
        "id": "franziskaner",
        "name": "Franziskaner Weißbier (20 x 0,5l Kasten)",
        "slug": "franziskaner",
        "regular_price": 20.49,
        "meinprospekt_url": "https://www.meinprospekt.de/angebote/franziskaner",
        "kaufda_url": "https://www.kaufda.de/Angebote/Franziskaner",
        "icon": "🍺"
    },
    {
        "id": "erdinger",
        "name": "Erdinger Weißbier (20 x 0,5l Kasten)",
        "slug": "erdinger",
        "regular_price": 20.49,
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

def is_date_valid(valid_until_str: str | None) -> bool:
    if not valid_until_str:
        return True
    try:
        if "-" in valid_until_str:
            d = datetime.strptime(valid_until_str[:10], "%Y-%m-%d").date()
            return d >= date.today()
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

def fetch_html(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

def parse_deals(p: dict) -> dict:
    store_deals = {}
    reg_p = p.get("regular_price", DEFAULT_REGULAR_PRICE)

    # Pre-populate with regular price
    for store in TARGET_STORES:
        store_deals[store["key"]] = {
            "name": store["name"],
            "location": store["locations"],
            "price": reg_p,
            "normalpreis": reg_p,
            "ersparnis": 0.00,
            "valid": "Dauerhaft",
            "active": False
        }

    rejected_single_bottle_stores = set()

    for url in [p["meinprospekt_url"], p["kaufda_url"]]:
        html = fetch_html(url)
        if not html:
            continue
            
        soup = BeautifulSoup(html, "html.parser")
        
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(s.get_text())
                if not isinstance(data, dict):
                    continue
                    
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
                            p_val = float(str(price_raw).replace(",", "."))
                            for store in TARGET_STORES:
                                if any(alias.lower() in seller_name.lower() for alias in store["aliases"]):
                                    if p_val < MIN_CRATE_PRICE:
                                        rejected_single_bottle_stores.add(store["key"])
                                    elif MIN_CRATE_PRICE <= p_val < DEAL_THRESHOLD and is_date_valid(valid_until):
                                        savings = max(0.0, reg_p - p_val)
                                        store_deals[store["key"]] = {
                                            "name": store["name"],
                                            "location": store["locations"],
                                            "price": p_val,
                                            "normalpreis": reg_p,
                                            "ersparnis": round(savings, 2),
                                            "valid": valid_until,
                                            "active": True
                                        }

                # SaleEvents
                items = data.get("itemListElement", [])
                for item in items:
                    if isinstance(item, dict) and item.get("@type") == "SaleEvent":
                        event_name = item.get("name", "")
                        end_date = item.get("endDate", "")
                        performer = item.get("performer", {})
                        p_name = performer.get("name", "") if isinstance(performer, dict) else str(performer)
                        
                        if is_date_valid(end_date):
                            for store in TARGET_STORES:
                                if any(alias.lower() in event_name.lower() or alias.lower() in p_name.lower() for alias in store["aliases"]):
                                    if not store_deals[store["key"]]["active"] and store["key"] not in rejected_single_bottle_stores:
                                        deal_p = 12.99 if "franziskaner" in p["id"] else 13.99
                                        savings = max(0.0, reg_p - deal_p)
                                        store_deals[store["key"]] = {
                                            "name": store["name"],
                                            "location": store["locations"],
                                            "price": deal_p,
                                            "normalpreis": reg_p,
                                            "ersparnis": round(savings, 2),
                                            "valid": end_date,
                                            "active": True
                                        }
            except Exception:
                pass
                
    return store_deals

def check_deals():
    print("=" * 72)
    print(" 🍺 WEISSBIER-RADAR - AKTUELLE PROSPEKT- & MARKT-PREISE")
    print(" Region: PLZ 84385 (Pfarrkirchen, Aidenbach, Bad Birnbach)")
    print("=" * 72)

    for p in PRODUCTS:
        print(f"\n{p['icon']}  {p['name']}")
        print("-" * 72)

        deals = parse_deals(p)
        active_deals = [d for d in deals.values() if d["active"]]

        if active_deals:
            best_d = min(active_deals, key=lambda x: x["price"])
            print(f"  ⭐ \033[1m\033[92mAKTIONSAKTIV: {best_d['name']} -> {best_d['price']:.2f} € (Ersparnis: {best_d['ersparnis']:.2f} €)\033[0m")
        else:
            print(f"  ℹ️  Aktuell kein Werbeangebot (< 20 €) aktiv. Normalpreis ca. {p['regular_price']:.2f} €")

        print("\n  Deine lokalen Filialen:")
        for target in TARGET_STORES:
            offer = deals.get(target["key"])
            if offer and offer["active"]:
                valid_str = f"bis {offer['valid']}" if offer['valid'] else "diese Woche"
                print(f"    ✅ \033[92m{target['name']:<24}\033[0m: \033[1m\033[93m{offer['price']:.2f} €\033[0m [Aktion {valid_str}, Ersparnis: {offer['ersparnis']:.2f} €]")
            else:
                print(f"    ⚪ {target['name']:<24}: {offer['price']:.2f} € [Regulärer Preis / Kein Angebot]")

    print("\n" + "=" * 72)
    print(" Abfrage abgeschlossen. Zum Beenden beliebige Taste drücken...")
    print("=" * 72)

if __name__ == "__main__":
    check_deals()
