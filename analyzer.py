"""Core analysis engine for Shopify app events.

Works directly with plain dicts from CSV — no data model classes.
Ported from jisrot/src/analyzing.rs.

Two-phase analysis:
  1. build_base_data() — count events, filter exclusions, build merchant dicts
  2. analyze_details() — derive installed/subscription status, churn rates, plan details
"""

from __future__ import annotations

import copy
import re
from datetime import datetime
from pathlib import Path

from data_io import (
    parse_time_str,
    read_events_from_csv,
    read_excluding_def_from_json,
    read_excluding_def_from_json_str,
    read_pricing_def_from_json,
    read_pricing_def_from_json_str,
    write_json,
)
from definitions import (
    BillingCycle,
    EVENT_TIME_PATTERN,
    FIELD_DATE,
    FIELD_DETAILS,
    FIELD_EVENT,
    FIELD_SHOP_DOMAIN,
    INSTALLED_STRING,
    NONE,
    ONE_TIME_ACTIVATED_STRINGS,
    STORE_CLOSED_STRING,
    STORE_REOPENED_STRING,
    SUBSCRIPTION_ACTIVATED_STRINGS,
    SUBSCRIPTION_CANCELED_STRINGS,
    SUBSCRIPTION_STATUS_ACTIVE,
    SUBSCRIPTION_STATUS_CANCELED,
    UNINSTALLED_OLD_STRING,
    UNINSTALLED_STRING,
    YEARLY_PATTERN,
    data,
    message,
    ui,
)


# ═══════════════════════════════════════════════════════════════════════
# Helpers — compile regex & create fresh data dicts
# ═══════════════════════════════════════════════════════════════════════

def _re(pattern: str, case_sensitive: bool = True) -> re.Pattern:
    """Compile a regex, optionally case-insensitive."""
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(pattern, flags)


def _match(pat: re.Pattern, text: str) -> bool:
    return bool(pat.search(text))


def _new_sub_stats_counter(subscription_plans: list[dict]) -> dict:
    """Create a fresh subscription stats counter dict."""
    monthly = {}
    yearly = {}
    for plan in subscription_plans:
        monthly[plan["code"]] = 0
        yearly[plan["code"]] = 0
    return {"monthly_counts": monthly, "yearly_counts": yearly}


def _new_detailed_sub_stats(subscription_plans: list[dict]) -> dict:
    """Create a fresh detailed subscription stats dict with all 5 counters."""
    return {
        "new_sub": _new_sub_stats_counter(subscription_plans),
        "canceled_sub": _new_sub_stats_counter(subscription_plans),
        "sub_growth": _new_sub_stats_counter(subscription_plans),
        "all_new_sub": _new_sub_stats_counter(subscription_plans),
        "all_canceled_sub": _new_sub_stats_counter(subscription_plans),
    }


def _increase_sub_counter(
    counter: dict,
    plan: dict,
    billing_cycle: BillingCycle,
    count: int = 1,
) -> None:
    """Increment a subscription stats counter for a given plan + billing cycle."""
    key = "monthly_counts" if billing_cycle == BillingCycle.Monthly else "yearly_counts"
    code = plan["code"]
    if code in counter[key]:
        counter[key][code] += count
    else:
        raise KeyError(
            f"[SubscriptionStatsCounter] plan '{code}' not found in {key}"
        )


def _new_merchant(shop_domain: str, one_time_packs: list[dict]) -> dict:
    """Create a fresh merchant dict with counters initialized."""
    return {
        "shop_domain": shop_domain,
        "checked": False,
        "installed_count": 0,
        "uninstalled_count": 0,
        "store_closed_count": 0,
        "store_reopened_count": 0,
        "installing_events": [],
        "subscription_activated_count": 0,
        "subscription_canceled_count": 0,
        "subscription_events": [],
        "one_time_count": 0,
        "one_time_details": {pack["code"]: 0 for pack in one_time_packs},
        "one_time_events": [],
        "installed_status": NONE,
        "subscription_status": NONE,
        "last_new_sub_plan": None,
        "last_new_sub_billing_cycle": None,
        "first_canceled_sub_plan": None,
        "first_canceled_sub_billing_cycle": None,
    }


def _new_total_stats(pricing_defs: dict) -> dict:
    """Create a fresh total stats dict with counters initialized."""
    return {
        "start_time": None,
        "end_time": None,
        "start_time_str": NONE,
        "end_time_str": NONE,
        "installed_count": 0,
        "uninstalled_count": 0,
        "old_uninstalled_count": 0,
        "total_churn_rate": 0.0,
        "churn_rate": 0.0,
        "merchant_growth": 0,
        "store_closed_count": 0,
        "store_reopened_count": 0,
        "one_time_count": 0,
        "one_time_details": {
            pack["code"]: 0 for pack in pricing_defs.get("one_times", [])
        },
        "new_sub_count": 0,
        "canceled_sub_count": 0,
        "sub_growth": 0,
        "sub_stats_details": _new_detailed_sub_stats(
            pricing_defs.get("subscriptions", [])
        ),
        "paid_growth": 0,
    }


# ═══════════════════════════════════════════════════════════════════════
# Phase 1: Base data building
# ═══════════════════════════════════════════════════════════════════════


def build_base_data(
    app_event_list: list[dict],
    pricing_defs: dict,
    excluding_def: dict,
    case_sensitive_regex: bool,
) -> tuple[dict, dict]:
    """Build base data from app event list.

    Counts install/uninstall/store-closed events, one-time charges,
    and subscription activations/cancellations. Applies exclusion filter.

    Returns (total_stats, merchants) as plain dicts.
    """
    merchants: dict[str, dict] = {}
    stats = _new_total_stats(pricing_defs)

    if not app_event_list:
        return stats, merchants

    # ── Set time range from first & last events ──────────────────
    first_time = parse_time_str(
        app_event_list[0].get(FIELD_DATE, ""), EVENT_TIME_PATTERN
    )
    last_time = parse_time_str(
        app_event_list[-1].get(FIELD_DATE, ""), EVENT_TIME_PATTERN
    )
    stats["start_time"] = first_time
    stats["end_time"] = last_time
    if first_time:
        stats["start_time_str"] = first_time.strftime("%b%d")
    if last_time:
        stats["end_time_str"] = last_time.strftime("%b%d")

    excluding_field = excluding_def["excluding_field"]
    excluding_pattern = excluding_def["excluding_pattern"]
    one_time_packs = pricing_defs.get("one_times", [])

    for row in app_event_list:
        # ── Exclusion check ──────────────────────────────────────
        check_data = row.get(excluding_field, "")

        if case_sensitive_regex:
            excl_re = _re(excluding_pattern, True)
            if _match(excl_re, check_data):
                continue
        else:
            excl_re = _re(excluding_pattern.lower(), True)
            if _match(excl_re, check_data) or _match(excl_re, check_data.lower()):
                continue

        # ── Get or create merchant ───────────────────────────────
        domain = row.get(FIELD_SHOP_DOMAIN, "")
        if domain in merchants:
            merchant = copy.deepcopy(merchants[domain])
        else:
            merchant = _new_merchant(domain, one_time_packs)

        event_type = row.get(FIELD_EVENT, "")
        details = row.get(FIELD_DETAILS, "")

        # ── Count Install ────────────────────────────────────────
        if _match(_re(INSTALLED_STRING), event_type):
            stats["installed_count"] += 1
            merchant["installed_count"] += 1
            merchant["installing_events"].append(row)
            merchants[domain] = merchant
            continue

        # ── Count Uninstall ──────────────────────────────────────
        if _match(_re(UNINSTALLED_STRING), event_type):
            stats["uninstalled_count"] += 1
            merchant["uninstalled_count"] += 1
            merchant["installing_events"].append(row)
            merchants[domain] = merchant
            continue

        # ── Count Store closed ───────────────────────────────────
        if _match(_re(STORE_CLOSED_STRING), event_type):
            stats["store_closed_count"] += 1
            merchant["store_closed_count"] += 1
            merchant["installing_events"].append(row)
            merchants[domain] = merchant
            continue

        # ── Count Store re-opened ────────────────────────────────
        if _match(_re(STORE_REOPENED_STRING), event_type):
            stats["store_reopened_count"] += 1
            merchant["store_reopened_count"] += 1
            merchant["installing_events"].append(row)
            merchants[domain] = merchant
            continue

        # ── Count One-Time charges ───────────────────────────────
        if event_type in ONE_TIME_ACTIVATED_STRINGS:
            stats["one_time_count"] += 1
            merchant["one_time_count"] += 1
            merchant["one_time_events"].append(row)

            for pack in one_time_packs:
                pack_re = _re(pack["regex_pattern"], case_sensitive_regex)
                if _match(pack_re, details) or (
                    not case_sensitive_regex
                    and _match(pack_re, details.lower())
                ):
                    code = pack["code"]
                    stats["one_time_details"][code] += 1
                    merchant["one_time_details"][code] += 1
                    break

            merchants[domain] = merchant
            continue

        # ── Count Subscription activations ───────────────────────
        if event_type in SUBSCRIPTION_ACTIVATED_STRINGS:
            merchant["subscription_activated_count"] += 1
            merchant["subscription_events"].append(row)
            merchants[domain] = merchant
            continue

        # ── Count Subscription cancellations ─────────────────────
        if event_type in SUBSCRIPTION_CANCELED_STRINGS:
            merchant["subscription_canceled_count"] += 1
            merchant["subscription_events"].append(row)
            merchants[domain] = merchant
            continue

    # ── Calculate pre-detail stats ───────────────────────────────
    stats["merchant_growth"] = (
        stats["installed_count"]
        + stats["store_reopened_count"]
        - stats["uninstalled_count"]
        - stats["store_closed_count"]
    )

    if stats["installed_count"] > 0:
        stats["total_churn_rate"] = (
            stats["uninstalled_count"] / stats["installed_count"]
        ) * 100.0

    return stats, merchants


# ═══════════════════════════════════════════════════════════════════════
# Phase 2: Detailed analysis
# ═══════════════════════════════════════════════════════════════════════


def analyze_details(
    stats: dict,
    merchants: dict[str, dict],
    pricing_defs: dict,
    case_sensitive_regex: bool,
) -> None:
    """Analyze subscription-related data from base data (mutates in place)."""
    subscriptions = pricing_defs.get("subscriptions", [])

    for merchant in merchants.values():
        # ── Determine installed status ───────────────────────────
        delta = (
            merchant["installed_count"]
            + merchant["store_reopened_count"]
            - merchant["uninstalled_count"]
            - merchant["store_closed_count"]
        )

        if delta > 0:
            merchant["installed_status"] = INSTALLED_STRING
        elif delta < 0:
            merchant["installed_status"] = UNINSTALLED_STRING
            installing = merchant["installing_events"]
            if (
                len(installing) > 0
                and installing[0].get(FIELD_EVENT, "") == UNINSTALLED_STRING
            ):
                merchant["installed_status"] = UNINSTALLED_OLD_STRING
                stats["old_uninstalled_count"] += 1
        else:
            merchant["installed_status"] = NONE

        # ── Determine subscription status ────────────────────────
        sub_delta = (
            merchant["subscription_activated_count"]
            - merchant["subscription_canceled_count"]
        )

        if sub_delta > 0:
            merchant["subscription_status"] = SUBSCRIPTION_STATUS_ACTIVE
            stats["new_sub_count"] += 1
        elif sub_delta < 0:
            merchant["subscription_status"] = SUBSCRIPTION_STATUS_CANCELED
            stats["canceled_sub_count"] += 1
        else:
            merchant["subscription_status"] = NONE

        # ── Last new subscription (reverse order) ────────────────
        for row in reversed(merchant["subscription_events"]):
            if row.get(FIELD_EVENT, "") in SUBSCRIPTION_ACTIVATED_STRINGS:
                details = row.get(FIELD_DETAILS, "")
                for plan in subscriptions:
                    plan_re = _re(plan["regex_pattern"], case_sensitive_regex)
                    if _match(plan_re, details) or (
                        not case_sensitive_regex
                        and _match(plan_re, details.lower())
                    ):
                        merchant["last_new_sub_plan"] = plan

                        # Determine billing cycle
                        year_re = _re(YEARLY_PATTERN, case_sensitive_regex)
                        if _match(year_re, details) or (
                            not case_sensitive_regex
                            and _match(year_re, details.lower())
                        ):
                            merchant["last_new_sub_billing_cycle"] = BillingCycle.Yearly
                        else:
                            merchant["last_new_sub_billing_cycle"] = BillingCycle.Monthly

                        ssd = stats["sub_stats_details"]

                        # all_new_sub
                        _increase_sub_counter(
                            ssd["all_new_sub"],
                            plan,
                            merchant["last_new_sub_billing_cycle"],
                        )

                        # new_sub (only if currently active)
                        if merchant["subscription_status"] == SUBSCRIPTION_STATUS_ACTIVE:
                            _increase_sub_counter(
                                ssd["new_sub"],
                                plan,
                                merchant["last_new_sub_billing_cycle"],
                            )

                        break
                break

        # ── First canceled subscription (forward order) ──────────
        # NOTE: Original Rust code always uses case-sensitive matching
        # for canceled subscription plan detection (analyzing.rs:280-281).
        for row in merchant["subscription_events"]:
            if row.get(FIELD_EVENT, "") in SUBSCRIPTION_CANCELED_STRINGS:
                details = row.get(FIELD_DETAILS, "")
                for plan in subscriptions:
                    plan_re = _re(plan["regex_pattern"], True)  # always case-sensitive
                    if _match(plan_re, details):
                        merchant["first_canceled_sub_plan"] = plan

                        year_re = _re(YEARLY_PATTERN, True)
                        if _match(year_re, details):
                            merchant["first_canceled_sub_billing_cycle"] = BillingCycle.Yearly
                        else:
                            merchant["first_canceled_sub_billing_cycle"] = BillingCycle.Monthly

                        ssd = stats["sub_stats_details"]

                        # all_canceled_sub
                        _increase_sub_counter(
                            ssd["all_canceled_sub"],
                            plan,
                            merchant["first_canceled_sub_billing_cycle"],
                        )

                        # canceled_sub (only if currently canceled)
                        if merchant["subscription_status"] == SUBSCRIPTION_STATUS_CANCELED:
                            _increase_sub_counter(
                                ssd["canceled_sub"],
                                plan,
                                merchant["first_canceled_sub_billing_cycle"],
                            )

                        break
                break

        # ── Update final total stats ─────────────────────────────
        if stats["installed_count"] > 0:
            stats["churn_rate"] = (
                (stats["uninstalled_count"] - stats["old_uninstalled_count"])
                / stats["installed_count"]
            ) * 100.0
        else:
            stats["churn_rate"] = 0.0

        stats["sub_growth"] = stats["new_sub_count"] - stats["canceled_sub_count"]
        stats["paid_growth"] = stats["sub_growth"] + stats["one_time_count"]

        # ── Sub growth details ───────────────────────────────────
        ssd = stats["sub_stats_details"]

        for plan_code in ssd["new_sub"]["monthly_counts"]:
            new_val = ssd["new_sub"]["monthly_counts"][plan_code]
            canceled_val = ssd["canceled_sub"]["monthly_counts"].get(plan_code, 0)
            ssd["sub_growth"]["monthly_counts"][plan_code] = new_val - canceled_val

        for plan_code in ssd["new_sub"]["yearly_counts"]:
            new_val = ssd["new_sub"]["yearly_counts"][plan_code]
            canceled_val = ssd["canceled_sub"]["yearly_counts"].get(plan_code, 0)
            ssd["sub_growth"]["yearly_counts"][plan_code] = new_val - canceled_val


# ═══════════════════════════════════════════════════════════════════════
# Orchestration
# ═══════════════════════════════════════════════════════════════════════


def analyze_events_list(
    event_list: list[dict],
    pricing_defs: dict,
    excluding_defs: dict,
    case_sensitive_regex: bool,
) -> tuple[dict, dict]:
    """Run full two-phase analysis on an event list.

    Returns (total_stats, merchants) as plain dicts.
    """
    stats, merchants = build_base_data(
        event_list, pricing_defs, excluding_defs, case_sensitive_regex
    )
    analyze_details(stats, merchants, pricing_defs, case_sensitive_regex)
    return stats, merchants


def analyze_file(
    event_history_file: Path,
    pricing_defs: dict,
    excluding_defs: dict,
    case_sensitive_regex: bool,
    out_folder: Path,
    out_file_total_stats_pref: str,
    out_file_merchant_data_pref: str | None,
    out_file_app_events_pref: str | None,
) -> str:
    """Analyze a single CSV file and write output JSON. Returns success message."""
    event_list = read_events_from_csv(event_history_file)

    stats, merchant_data = analyze_events_list(
        event_list, pricing_defs, excluding_defs, case_sensitive_regex
    )

    # ── Write total stats (always) ───────────────────────────────
    out_total = out_folder / (
        f"{out_file_total_stats_pref}_"
        f"{stats['start_time_str']}_"
        f"{stats['end_time_str']}.json"
    )
    write_json(out_total, stats)
    msg = (
        f"{data.TOTAL_STATS} "
        f"{message.success.SPECIFIC_DATA_WRITTEN_FILE} "
        f"{out_total}"
    )

    # ── Optionally write merchant data ───────────────────────────
    if out_file_merchant_data_pref:
        out_m = out_folder / (
            f"{out_file_merchant_data_pref}_"
            f"{stats['start_time_str']}_"
            f"{stats['end_time_str']}.json"
        )
        write_json(out_m, merchant_data)
        msg += (
            f"\n{data.MERCHANT_DATA} "
            f"{message.success.SPECIFIC_DATA_WRITTEN_FILE} "
            f"{out_m}"
        )

    # ── Optionally write app events ──────────────────────────────
    if out_file_app_events_pref:
        out_e = out_folder / (
            f"{out_file_app_events_pref}_"
            f"{stats['start_time_str']}_"
            f"{stats['end_time_str']}.json"
        )
        write_json(out_e, event_list)
        msg += (
            f"\n{data.APP_EVENTS} "
            f"{message.success.SPECIFIC_DATA_WRITTEN_FILE} "
            f"{out_e}"
        )

    return msg


def analyze_from_gui(
    event_history_file_list: list[Path] | None,
    selected_pricing_defs_option: dict,
    selected_excluding_defs_option: dict,
    pricing_defs_file: Path | None,
    excluding_defs_file: Path | None,
    debug_mode: bool,
    case_sensitive_regex: bool,
) -> str:
    """Entry point called from the GUI. Returns success message or raises ValueError."""
    # ── Resolve pricing definitions ──────────────────────────────
    if selected_pricing_defs_option["value"] == ui.OPTION_CUSTOM_VALUE:
        if pricing_defs_file:
            pricing_defs = read_pricing_def_from_json(pricing_defs_file)
        else:
            raise ValueError(
                f"{data.KIND_CUSTOM} {data.PRICING_DEFS} "
                f"{message.error.FILE_NOT_CHOSEN}!"
            )
    else:
        pricing_defs = read_pricing_def_from_json_str(
            selected_pricing_defs_option["connected_data"] or "{}"
        )

    # ── Resolve excluding definitions ────────────────────────────
    if selected_excluding_defs_option["value"] == ui.OPTION_CUSTOM_VALUE:
        if excluding_defs_file:
            excluding_defs = read_excluding_def_from_json(excluding_defs_file)
        else:
            raise ValueError(
                f"{data.KIND_CUSTOM} {data.EXCLUDING_DEFS} "
                f"{message.error.FILE_NOT_CHOSEN}!"
            )
    else:
        excluding_defs = read_excluding_def_from_json_str(
            selected_excluding_defs_option["connected_data"] or "{}"
        )

    # ── Validate input files ─────────────────────────────────────
    if not event_history_file_list:
        raise ValueError(
            f"{data.APP_EVENTS} {message.error.FILE_NOT_CHOSEN}!"
        )

    out_folder = Path.cwd() / data.OUT_FOLDER_NAME
    errors: list[str] = []

    out_total_pref = data.TOTAL_STATS.replace(" ", "_").lower()

    out_merchant_pref: str | None = None
    out_events_pref: str | None = None

    success_msg = (
        f"{data.TOTAL_STATS} {message.success.SPECIFIC_DATA_WRITTEN_FILE}\n"
    )

    if debug_mode:
        success_msg += (
            f"{data.MERCHANT_DATA} {message.success.SPECIFIC_DATA_WRITTEN_FILE}\n"
            f"{data.APP_EVENTS} {message.success.SPECIFIC_DATA_WRITTEN_FILE}"
        )
        out_merchant_pref = data.MERCHANT_DATA.replace(" ", "_").lower()
        out_events_pref = data.APP_EVENTS.replace(" ", "_").lower()

    for f in event_history_file_list:
        try:
            analyze_file(
                f,
                pricing_defs,
                excluding_defs,
                case_sensitive_regex,
                out_folder,
                out_total_pref,
                out_merchant_pref,
                out_events_pref,
            )
        except Exception as e:
            errors.append(str(e))

    if errors:
        raise ValueError("".join(errors))

    return success_msg
