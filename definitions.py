"""String constants, UI labels, and built-in JSON definitions.

Ported from jisrot/src/definitions/.
"""

from enum import StrEnum


class BillingCycle(StrEnum):
    Monthly = "Monthly"
    Yearly = "Yearly"


# ── Event type strings ──────────────────────────────────────────────

SUBSCRIPTION_CANCELED_STRINGS = [
    "Subscription charge canceled",
    "Subscription charge frozen",
]

SUBSCRIPTION_ACTIVATED_STRINGS = [
    "Subscription charge activated",
    "Subscription charge unfrozen",
]

ONE_TIME_ACTIVATED_STRINGS = ["Charge activated"]

INSTALLED_STRING = "Installed"
UNINSTALLED_STRING = "Uninstalled"
STORE_CLOSED_STRING = "Store closed"
STORE_REOPENED_STRING = "Store re-opened"

UNINSTALLED_OLD_STRING = "UninstalledOld"

# ── Status strings ──────────────────────────────────────────────────

SUBSCRIPTION_STATUS_CANCELED = "Canceled"
SUBSCRIPTION_STATUS_ACTIVE = "Active"

# ── CSV field names (match Shopify event history CSV headers) ───────

FIELD_DATE = "Date"
FIELD_EVENT = "Event"
FIELD_DETAILS = "Details"
FIELD_BILLING_ON = "Billing on"
FIELD_SHOP_DOMAIN = "Shop domain"
FIELD_SHOP_EMAIL = "Shop email"
FIELD_SHOP_NAME = "Shop name"
FIELD_SHOP_COUNTRY = "Shop country"

NONE = "None"

# ── Date/time patterns ──────────────────────────────────────────────

EVENT_TIME_PATTERN = "%Y-%m-%d %H:%M:%S UTC"
BILLING_ON_PATTERN = "%Y-%m-%d"

# ── Regex patterns ──────────────────────────────────────────────────

YEARLY_PATTERN = "Year"


# ── Messages ────────────────────────────────────────────────────────

class message:
    class success:
        SPECIFIC_DATA_WRITTEN_FILE = "is written to file"

    class error:
        FILE_NOT_CHOSEN = "File not chosen"


# ── Data labels ─────────────────────────────────────────────────────

class data:
    OUT_FOLDER_NAME = "Output"
    KIND_CUSTOM = "Custom"
    TOTAL_STATS = "Total Stats"
    MERCHANT_DATA = "Merchant Data"
    APP_EVENTS = "App Event List"
    PRICING_DEFS = "Pricing definitions"
    EXCLUDING_DEFS = "Excluding definitions"


# ── UI labels ───────────────────────────────────────────────────────

class ui:
    BTN_BROWSE_LBL = "Browse..."
    BTN_ANALYZE_LBL = "Analyze!"
    BTN_EVENT_FILE_PICKER_LBL = "Browse event history file..."

    SELECTOR_PRICING_DEFS_ID = "selector_pricing_defs"
    SELECTOR_EXCLUDING_DEFS_ID = "selector_excluding_defs"

    CHECKBOX_DEBUG_MODE_LBL = "Debug mode"
    CHECKBOX_CASE_SENSITIVE_REGEX_LBL = "Case-sensitive regex"

    OPTION_CUSTOM_VALUE = "custom"
    OPTION_CUSTOM_TEXT = "Custom"


# ── Built-in JSON definition strings ────────────────────────────────

MS_EXCLUDING_DEF_JSON_STRING = """{
    "excluding_field": "Shop email",
    "excluding_pattern": "magestore"
}"""

SBM_PRICING_DEF_JSON_STRING = """{
  "subscriptions": [
    {
      "code": "standard",
      "name": "Standard",
      "regex_pattern": "standard",
      "price": 7.99,
      "currency": "USD"
    },
    {
      "code": "pro",
      "name": "Pro",
      "regex_pattern": "pro",
      "price": 27.99,
      "currency": "USD"
    }
  ],
  "one_times": [
    {
      "code": "pack2k",
      "name": "2000 Labels",
      "regex_pattern": "2000",
      "price": 11.99,
      "currency": "USD"
    },
    {
      "code": "pack5k",
      "name": "5000 Labels",
      "regex_pattern": "5000",
      "price": 22.99,
      "currency": "USD"
    },
    {
      "code": "pack15k",
      "name": "15000 Labels",
      "regex_pattern": "15000",
      "price": 44.99,
      "currency": "USD"
    }
  ]
}"""

SPOP_PRICING_DEF_JSON_STRING = """{
  "subscriptions": [
    {
      "code": "Free",
      "name": "Free",
      "regex_pattern": "Free",
      "price": 8.99,
      "currency": "USD"
    },
    {
      "code": "Standard",
      "name": "Standard",
      "regex_pattern": "Standard",
      "price": 8.99,
      "currency": "USD"
    },
    {
      "code": "pro",
      "name": "Pro",
      "regex_pattern": "pro",
      "price": 59.99,
      "currency": "USD"
    }
  ],
  "one_times": []
}"""


# ── Pre-built UiOption dicts (plain dict, no class needed) ──────────

def _make_ui_option(value: str, text: str, connected_data: str | None = None) -> dict:
    """Create a plain dict for a UI combo-box option."""
    return {
        "value": value,
        "text": text,
        "connected_data": connected_data,
    }


EXCLUDING_DEFS_OPTION_MS = _make_ui_option(
    "magestore", "Magestore", MS_EXCLUDING_DEF_JSON_STRING
)

PRICING_DEFS_OPTION_SBM = _make_ui_option(
    "sbm", "MS Barcode", SBM_PRICING_DEF_JSON_STRING
)

PRICING_DEFS_OPTION_SPOP = _make_ui_option(
    "spop", "MS Order Printer", SPOP_PRICING_DEF_JSON_STRING
)

OPTION_CUSTOM = _make_ui_option("custom", "Custom", None)

EXCLUDING_DEFS_OPTION_LIST = [EXCLUDING_DEFS_OPTION_MS]
PRICING_DEFS_OPTION_LIST = [PRICING_DEFS_OPTION_SBM, PRICING_DEFS_OPTION_SPOP]
