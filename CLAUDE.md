# CLAUDE.md — AI Agent Instructions for pyjisaa

## Project Identity

- **Project**: `pyjisaa` — Python rewrite of `jisrot` (Shopify app event analyzer)
- **Source repo**: `../jisrot` (Rust codebase being migrated from)
- **Purpose**: Analyze Shopify app event history → structured JSON stats. Future: fetch events from Shopify Partner API.

## Migration Context (READ FIRST)

This project is a **Python rewrite** of the Rust codebase at `../jisrot`. The full original logic is documented in Claude memory — the AI should load it at session start.

**Target stack**: Python 3.12+ / PySide6 (GUI) / polars or pandas (data) / httpx (API) / pydantic (models)

**Original jisrot files to port**:
| Rust file | Python equivalent |
|-----------|-------------------|
| `src/models/data_model.rs` | `models.py` — AppEvent, Merchant, MerchantList, TotalStats, PricingDefs, etc. |
| `src/models/ui_model.rs` | Not needed — PySide6 handles UI state natively |
| `src/analyzing.rs` | `analyzer.py` — build_base_data() + analyze_details() |
| `src/data_io.rs` | `data_io.py` — CSV read, JSON read/write |
| `src/definitions/common.rs` | `definitions.py` — string constants |
| `src/definitions/strings.rs` | `definitions.py` — UI labels + built-in UiOption defs |
| `src/definitions/default_ms_*.rs` | `definitions.py` — embedded JSON strings |
| `src/app_egui.rs` | `gui.py` — PySide6 GUI |
| `src/main.rs` | `main.py` — entry point |

## Existing code in this repo
- `fetch_data/fetch_partner_api.py` — Shopify Partner API GraphQL client (keep, integrate later)
- `requirements.txt` — already has pandas, requests, gql, python-dotenv

## Key architecture decisions to preserve
1. Two-phase analysis: `build_base_data()` (counting) → `analyze_details()` (derived metrics)
2. `shop_domain` as primary key for merchant grouping
3. `case_sensitive_regex` flag flowing through all analysis layers
4. Event matching via `if/continue` chain (not if-else)
5. IndexMap-like ordering — use Python `dict` (ordered by insertion since 3.7)
6. UPSERT pattern for merchants in MerchantList

## Data flow (to reproduce)
```
CSV file(s) → read CSV → Vec<AppEvent> sorted by time
  → build_base_data(events, pricing_defs, excluding_def, case_sensitive)
    → exclusion filter → event type matching → counting → MerchantList
  → analyze_details(merchant_list, pricing_defs, case_sensitive)
    → installed_status, subscription_status, last/first sub plans, churn rates
  → write JSON output files
```

## Built-in definitions (to embed in Python)
- **SBM Barcode** (pricing): subscriptions=Standard($7.99)/Pro($27.99), one_times=2000($11.99)/5000($22.99)/15000($44.99)
- **SPOP Order Printer** (pricing): subscriptions=Free($8.99)/Standard($8.99)/Pro($59.99), one_times=[]
- **Magestore** (excluding): field="Shop email", pattern="magestore"

## Pending decisions
- polars vs pandas for data processing
- Whether to keep `fetch_partner_api.py` as-is or refactor
