"""
Constants for the Weissbier Radar integration.
"""

DOMAIN = "weissbier_radar"
NAME = "Weissbier Radar"
VERSION = "1.2.0"

# Default configuration values
DEFAULT_ZIP_CODE = "84385"
DEFAULT_SCAN_INTERVAL_HOURS = 6
DEFAULT_DEAL_THRESHOLD = 20.00
DEFAULT_REGULAR_PRICE = 20.49

# Supported beers / products
CONF_PRODUCTS = "products"
CONF_ZIP_CODE = "zip_code"
CONF_STORES = "stores"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_DEAL_THRESHOLD = "deal_threshold"

DEFAULT_PRODUCTS = [
    "franziskaner",
    "erdinger"
]

PRODUCT_DEFINITIONS = {
    "franziskaner": {
        "id": "franziskaner",
        "name": "Franziskaner Weißbier",
        "slug": "franziskaner",
        "regular_price": 20.49,
        "icon": "mdi:glass-mug-variant",
        "meinprospekt_url": "https://www.meinprospekt.de/angebote/franziskaner",
        "kaufda_url": "https://www.kaufda.de/Angebote/Franziskaner",
        "aktionspreis_url": "https://www.aktionspreis.de/angebote/franziskaner-kasten-20-x-0-5l"
    },
    "erdinger": {
        "id": "erdinger",
        "name": "Erdinger Weißbier",
        "slug": "erdinger",
        "regular_price": 20.49,
        "icon": "mdi:glass-mug",
        "meinprospekt_url": "https://www.meinprospekt.de/angebote/erdinger",
        "kaufda_url": "https://www.kaufda.de/Angebote/Erdinger",
        "aktionspreis_url": "https://www.aktionspreis.de/angebote/erdinger-kasten-20-x-0-5l"
    }
}

DEFAULT_STORES = [
    "netto-marken-discount",
    "edeka",
    "kaufland"
]

STORE_DEFINITIONS = {
    "netto-marken-discount": {
        "name": "Netto Marken-Discount",
        "aliases": ["Netto Marken-Discount", "Netto"],
        "icon": "mdi:storefront-outline",
        "locations": "Aidenbach, Pfarrkirchen"
    },
    "edeka": {
        "name": "Edeka",
        "aliases": ["Edeka", "EDEKA", "Edeka Center"],
        "icon": "mdi:store",
        "locations": "Pfarrkirchen, Aidenbach, Bad Birnbach"
    },
    "kaufland": {
        "name": "Kaufland",
        "aliases": ["Kaufland"],
        "icon": "mdi:cart-outline",
        "locations": "Pfarrkirchen"
    }
}
