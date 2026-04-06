import json
import os
import sys
from datetime import datetime

import requests

from africa_countries import slugify_country


API_BASE = "https://fdw.fews.net/api"
TOKEN_URL = "https://fdw.fews.net/api-token-auth/"


def normalize_date(value):
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        if text.endswith("Z"):
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(text)
        return dt.date().isoformat()
    except ValueError:
        return text[:10]


def format_date_short(value):
    text = normalize_date(value)
    if not text:
        return "Unknown"
    try:
        return datetime.fromisoformat(text).strftime("%b %Y")
    except ValueError:
        return text


def format_period(record):
    if not record:
        return "N/A"
    start = record.get("projection_start")
    end = record.get("projection_end")
    if start and end and start != end:
        return f"{format_date_short(start)} – {format_date_short(end)}"
    return format_date_short(start or end or record.get("reporting_date"))


def to_number(value):
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def sum_pct_phases(record):
    p3 = record.get("pct_phase3")
    p4 = record.get("pct_phase4")
    p5 = record.get("pct_phase5")
    if p3 is None and p4 is None and p5 is None:
        return None
    return to_number(p3) + to_number(p4) + to_number(p5)


def phase_level_text(value):
    level = round(to_number(value))
    if level >= 5:
        return "Phase 5 - Famine/Catastrophe"
    if level == 4:
        return "Phase 4 - Emergency"
    if level == 3:
        return "Phase 3 - Crisis"
    if level == 2:
        return "Phase 2 - Stressed"
    if level == 1:
        return "Phase 1 - Minimal"
    return "Unclassified"


def phase_grouping_text(value):
    level = round(to_number(value))
    if level >= 5:
        return "Phase 5 (Catastrophe/Famine)"
    if level >= 4:
        return "Phase 4+ (Emergency or worse)"
    if level >= 3:
        return "Phase 3+ (Crisis or worse)"
    if level >= 1:
        return "Phase 1-2 (Minimal to Stressed)"
    return "Grouping unavailable"


def is_current_situation(label):
    return "current" in str(label or "").lower()


def is_projection_scenario(label):
    text = str(label or "").lower()
    return any(term in text for term in ("projection", "most likely", "near term", "ml"))


def is_phase3_plus(record):
    phase = str(record.get("phase") or "").strip().lower()
    return phase == "3+" or phase == "3" or phase.startswith("3")


def first_text(record, keys, default=""):
    for key in keys:
        value = str(record.get(key) or "").strip()
        if value:
            return value
    return default


def pick_latest_record(records, predicate=None, date_key="reporting_date"):
    filtered = [r for r in (records or []) if predicate is None or predicate(r)]
    if not filtered:
        return None
    filtered.sort(key=lambda item: normalize_date(item.get(date_key)), reverse=True)
    return filtered[0]


def pick_previous_record(records, latest, predicate=None, date_key="reporting_date"):
    if not latest:
        return None
    latest_date = normalize_date(latest.get(date_key))
    filtered = []
    for item in records or []:
        if predicate is not None and not predicate(item):
            continue
        if normalize_date(item.get(date_key)) < latest_date:
            filtered.append(item)
    if not filtered:
        return None
    filtered.sort(key=lambda item: normalize_date(item.get(date_key)), reverse=True)
    return filtered[0]


def paged_get(session, endpoint, params, max_pages=2):
    results = []
    next_url = f"{API_BASE}/{endpoint}/"
    next_params = params
    for _ in range(max_pages):
        if not next_url:
            break
        response = session.get(next_url, params=next_params, timeout=60)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            return payload
        page_results = payload.get("results") or []
        results.extend(page_results)
        next_url = payload.get("next")
        next_params = None
    return results


def build_session(username, password):
    token_resp = requests.post(TOKEN_URL, data={"username": username, "password": password}, timeout=30)
    token_resp.raise_for_status()
    token = token_resp.json()["token"]
    session = requests.Session()
    session.headers.update({"Authorization": "JWT " + token})
    return session


def resolve_country(session, country_input):
    query = str(country_input or "").strip()
    rows = paged_get(session, "country", {"format": "json", "page_size": 500}, max_pages=1)
    lower = query.lower()
    for row in rows:
        iso2 = str(row.get("iso3166a2") or "").upper()
        iso3 = str(row.get("iso3166a3") or "").upper()
        names = [
            row.get("preferred_name"),
            row.get("iso_en_name"),
            row.get("iso_en_ro_name"),
            row.get("country"),
            row.get("name"),
        ]
        names = [str(name or "").strip().lower() for name in names if str(name or "").strip()]
        if len(query) == 2 and iso2 == query.upper():
            return {"iso2": iso2, "country": row.get("preferred_name") or row.get("country") or query}
        if len(query) == 3 and iso3 == query.upper():
            return {"iso2": iso2, "country": row.get("preferred_name") or row.get("country") or query}
        if lower in names:
            return {"iso2": iso2, "country": row.get("preferred_name") or row.get("country") or query}

    for row in rows:
        name = str(row.get("preferred_name") or row.get("iso_en_name") or row.get("country") or "").lower()
        if lower and lower in name:
            return {"iso2": str(row.get("iso3166a2") or "").upper(), "country": row.get("preferred_name") or row.get("country") or query}

    raise RuntimeError(f"Could not resolve FEWS country code for '{country_input}'")


def fetch_phase_records(session, iso2):
    params = [
        ("format", "json"),
        ("page_size", "100"),
        ("ordering", "-reporting_date"),
        ("unit_type", "admin0"),
        ("country_code", iso2),
        ("classification_scale", "IPC30"),
        ("classification_scale", "IPC31"),
    ]
    admin0 = paged_get(session, "ipcphase", params, max_pages=2)
    if not admin0:
        params = [(k, v) for (k, v) in params if k != "classification_scale"]
        admin0 = paged_get(session, "ipcphase", params, max_pages=2)

    params = [
        ("format", "json"),
        ("page_size", "500"),
        ("ordering", "-reporting_date"),
        ("country_code", iso2),
        ("classification_scale", "IPC30"),
        ("classification_scale", "IPC31"),
    ]
    all_records = paged_get(session, "ipcphase", params, max_pages=2)
    if not all_records:
        params = [(k, v) for (k, v) in params if k != "classification_scale"]
        all_records = paged_get(session, "ipcphase", params, max_pages=2)

    merged = {}
    for record in admin0 + all_records:
        key = str(record.get("id") or "") or f"{record.get('fnid')}|{record.get('reporting_date')}|{record.get('scenario')}|{record.get('geographic_unit_name')}"
        merged[key] = record
    return list(merged.values())


def fetch_population_records(session, iso2):
    params = [
        ("format", "json"),
        ("page_size", "500"),
        ("ordering", "-projection_end"),
        ("country_code", iso2),
        ("classification_scale", "IPC30"),
        ("classification_scale", "IPC31"),
    ]
    records = paged_get(session, "ipcpopulationsize", params, max_pages=2)
    if not records:
        params = [(k, v) for (k, v) in params if k != "classification_scale"]
        records = paged_get(session, "ipcpopulationsize", params, max_pages=2)
    return records


def summarize_phase(records, pop_records):
    if not records:
        raise RuntimeError("No FEWS IPC phase records found")

    latest_projection_admin0 = pick_latest_record(
        records,
        lambda item: str(item.get("unit_type") or "").lower() == "admin0" and is_projection_scenario(item.get("scenario_name")),
    )
    latest_current_admin0 = pick_latest_record(
        records,
        lambda item: str(item.get("unit_type") or "").lower() == "admin0" and is_current_situation(item.get("scenario_name")),
    )
    latest_country = latest_projection_admin0 or latest_current_admin0 or pick_latest_record(
        records,
        lambda item: str(item.get("unit_type") or "").lower() == "admin0",
    ) or pick_latest_record(records)

    latest_projection_date = normalize_date((latest_projection_admin0 or {}).get("reporting_date"))
    latest_current_date = normalize_date((latest_current_admin0 or {}).get("reporting_date"))

    def hotspot_filter(item, target_date, scenario_fn):
        unit = str(item.get("unit_type") or "").lower()
        return (
            target_date
            and normalize_date(item.get("reporting_date")) == target_date
            and scenario_fn(item.get("scenario_name"))
            and unit in {"admin1", "fsc_admin", "fsc_admin_lhz"}
            and to_number(item.get("value")) >= 3
        )

    projection_hotspots = sorted(
        [item for item in records if hotspot_filter(item, latest_projection_date, is_projection_scenario)],
        key=lambda item: (-to_number(item.get("value")), first_text(item, ["geographic_unit_name"], "Unknown ADM1")),
    )[:12]
    current_hotspots = sorted(
        [item for item in records if hotspot_filter(item, latest_current_date, is_current_situation)],
        key=lambda item: (-to_number(item.get("value")), first_text(item, ["geographic_unit_name"], "Unknown ADM1")),
    )[:12]

    current_pct3p = sum_pct_phases(latest_current_admin0 or {}) if latest_current_admin0 else None
    projected_pct3p = sum_pct_phases(latest_projection_admin0 or {}) if latest_projection_admin0 else None
    forward_pct_change = None
    if current_pct3p not in (None, 0) and projected_pct3p is not None:
        forward_pct_change = ((projected_pct3p - current_pct3p) / current_pct3p) * 100

    previous_projection = pick_previous_record(
        records,
        latest_projection_admin0,
        lambda item: str(item.get("unit_type") or "").lower() == "admin0" and is_projection_scenario(item.get("scenario_name")),
    )
    projected_pct_prev = sum_pct_phases(previous_projection or {}) if previous_projection else None
    projected_pct_trend = None
    if projected_pct_prev not in (None, 0) and projected_pct3p is not None:
        projected_pct_trend = ((projected_pct3p - projected_pct_prev) / projected_pct_prev) * 100

    current_status_text = phase_level_text((latest_current_admin0 or {}).get("value")) if latest_current_admin0 else "Unavailable"
    projection_status_text = phase_level_text((latest_projection_admin0 or {}).get("value")) if latest_projection_admin0 else "Unavailable"

    def hotspot_text(items, fallback):
        if not items:
            return fallback
        return ", ".join(
            f"{first_text(item, ['geographic_unit_name'], 'Unknown ADM1')} (Phase {round(to_number(item.get('value'))):.0f})"
            for item in items
        )

    current_pop_record = pick_latest_record(
        pop_records,
        lambda item: is_phase3_plus(item) and is_current_situation(item.get("scenario_name")),
        date_key="projection_end",
    )
    projection_pop_record = pick_latest_record(
        pop_records,
        lambda item: is_phase3_plus(item) and is_projection_scenario(item.get("scenario_name")),
        date_key="projection_end",
    )

    primary_level = to_number((latest_projection_admin0 or latest_country or {}).get("value"))
    proj_emergency = [item for item in projection_hotspots if to_number(item.get("value")) >= 4]
    proj_famine = [item for item in projection_hotspots if to_number(item.get("value")) >= 5]
    cur_emergency = [item for item in current_hotspots if to_number(item.get("value")) >= 4]
    cur_famine = [item for item in current_hotspots if to_number(item.get("value")) >= 5]

    trend_parts = []
    if forward_pct_change is not None:
        trend_parts.append(f"{forward_pct_change:+.1f}% Phase 3+ share from current to projection")
    if projected_pct_trend is not None:
        trend_parts.append(f"{projected_pct_trend:+.1f}% vs previous projection period")

    return {
        "level": round(primary_level),
        "levelText": phase_grouping_text(primary_level),
        "riskScore": "Current: " + (f"{to_number(latest_current_admin0.get('value')):.1f}" if latest_current_admin0 else "N/A")
        + " | Projection: " + (f"{to_number(latest_projection_admin0.get('value')):.1f}" if latest_projection_admin0 else "N/A"),
        "status": "Current " + (current_status_text if latest_current_admin0 else "Unavailable")
        + " | Projection " + (projection_status_text if latest_projection_admin0 else "Unavailable"),
        "latestPeriod": "Current: " + (format_date_short((latest_current_admin0 or {}).get("reporting_date")) if latest_current_admin0 else "N/A")
        + " | Projection: " + (format_date_short((latest_projection_admin0 or {}).get("reporting_date")) if latest_projection_admin0 else "N/A"),
        "trend": " | ".join(trend_parts) if trend_parts else ("Trend unavailable (pct fields not published for this country)" if current_pct3p is None else "Insufficient data"),
        "adm1Summary": "See Current and Projection sections below",
        "famineSummary": "Projection Phase 3+/4+/5 areas: "
        + f"{len(projection_hotspots)}/{len(proj_emergency)}/{len(proj_famine)}"
        + " | Current Phase 3+/4+/5 areas: "
        + f"{len(current_hotspots)}/{len(cur_emergency)}/{len(cur_famine)}",
        "sections": [
            {
                "title": "Current Situation",
                "ipcPhase": f"IPC {current_status_text}" if latest_current_admin0 else "Unavailable",
                "population": (str(current_pop_record.get("population_range") or "") + " Phase 3+ in need").strip() if current_pop_record else "Population estimate unavailable",
                "period": format_period(current_pop_record) if current_pop_record else (format_date_short((latest_current_admin0 or {}).get("reporting_date")) if latest_current_admin0 else "N/A"),
                "hotspots": hotspot_text(current_hotspots, "No Phase 3+ ADM1 hotspots in latest current period"),
            },
            {
                "title": "Forward Projection",
                "ipcPhase": f"IPC {projection_status_text}" if latest_projection_admin0 else "Unavailable",
                "population": (str(projection_pop_record.get("population_range") or "") + " Phase 3+ in need").strip() if projection_pop_record else "Population estimate unavailable",
                "period": format_period(projection_pop_record) if projection_pop_record else (format_date_short((latest_projection_admin0 or {}).get("reporting_date")) if latest_projection_admin0 else "N/A"),
                "hotspots": hotspot_text(projection_hotspots, "No Phase 3+ ADM1 hotspots in latest projection period"),
            },
        ],
        "url": f"{API_BASE}/ipcphase/",
    }


def latest_records_by_date(records):
    dated = [record for record in records if normalize_date(record.get("reporting_date") or record.get("date") or record.get("start_date") or record.get("season_year"))]
    if not dated:
        return "", []
    latest_date = max(normalize_date(record.get("reporting_date") or record.get("date") or record.get("start_date") or record.get("season_year")) for record in dated)
    latest = [record for record in dated if normalize_date(record.get("reporting_date") or record.get("date") or record.get("start_date") or record.get("season_year")) == latest_date]
    return latest_date, latest


def build_market_card(records):
    if not records:
        return {
            "level": 0,
            "levelText": "Market data",
            "riskScore": "No FEWS market data",
            "status": "No market price records found",
            "latestPeriod": "Unknown",
            "trend": "Snapshot unavailable",
            "adm1Summary": "No market price records found for this country",
            "url": f"{API_BASE}/marketpricefacts/",
        }

    latest_date, latest = latest_records_by_date(records)
    latest_sorted = sorted(
        latest,
        key=lambda item: first_text(item, ["commodity_name", "commodity", "indicator_name", "cpcv2_name", "cpcv2"], "Unknown"),
    )[:12]
    lines = []
    for item in latest_sorted:
        commodity = first_text(item, ["commodity_name", "commodity", "indicator_name", "cpcv2_name", "cpcv2"], "Unknown commodity")
        market = first_text(item, ["market_name", "market", "geographic_unit_name", "admin_1", "admin_0"], "Unknown market")
        unit = first_text(item, ["unit_name", "unit", "currency", "currency_name"], "")
        value = first_text(item, ["description"], "")
        if not value:
            raw_value = item.get("value")
            value = str(raw_value) if raw_value not in (None, "") else "No value"
        lines.append(f"{commodity}: {value}{(' ' + unit) if unit else ''} ({market})")

    return {
        "level": 0,
        "levelText": "Market data",
        "riskScore": f"{len(latest)} records in latest period",
        "status": "Authenticated FEWS market price snapshot",
        "latestPeriod": format_date_short(latest_date),
        "trend": "Latest authenticated FEWS NET snapshot",
        "adm1Summary": " | ".join(lines) if lines else "No market price detail available",
        "url": f"{API_BASE}/marketpricefacts/",
    }


def build_trade_card(records):
    if not records:
        return {
            "level": 0,
            "levelText": "Trade flow data",
            "riskScore": "No FEWS trade data",
            "status": "No cross-border trade records found",
            "latestPeriod": "Unknown",
            "trend": "Snapshot unavailable",
            "adm1Summary": "No cross-border trade records found for this country",
            "url": f"{API_BASE}/tradeflowquantityvalue/",
        }

    latest_date, latest = latest_records_by_date(records)
    lines = []
    for item in latest[:12]:
        commodity = first_text(item, ["commodity_name", "commodity", "indicator_name", "cpcv2_name", "cpcv2"], "Unknown commodity")
        origin = first_text(item, ["origin_country_name", "origin_country", "source_country_name", "country_from_name"], "Unknown origin")
        destination = first_text(item, ["destination_country_name", "destination_country", "partner_country_name", "country_to_name"], "Unknown destination")
        unit = first_text(item, ["unit_name", "unit", "currency", "currency_name"], "")
        value = first_text(item, ["description"], "")
        if not value:
            for key in ("value", "quantity", "total_value", "usd_value", "volume"):
                if item.get(key) not in (None, ""):
                    value = str(item.get(key))
                    break
        lines.append(f"{commodity}: {value or 'No value'}{(' ' + unit) if unit else ''} ({origin} -> {destination})")

    return {
        "level": 0,
        "levelText": "Trade flow data",
        "riskScore": f"{len(latest)} records in latest period",
        "status": "Authenticated FEWS cross-border trade snapshot",
        "latestPeriod": format_date_short(latest_date),
        "trend": "Latest authenticated FEWS NET snapshot",
        "adm1Summary": " | ".join(lines) if lines else "No trade flow detail available",
        "url": f"{API_BASE}/tradeflowquantityvalue/",
    }


def build_crop_card(records):
    if not records:
        return {
            "level": 0,
            "levelText": "Crop production data",
            "riskScore": "No FEWS crop data",
            "status": "No crop production records found",
            "latestPeriod": "Unknown",
            "trend": "Snapshot unavailable",
            "adm1Summary": "No crop production records found for this country",
            "url": f"{API_BASE}/cropproductionfacts/",
        }

    latest_date, latest = latest_records_by_date(records)
    lines = []
    for item in latest[:12]:
        crop = first_text(item, ["crop_name", "commodity_name", "commodity", "indicator_name", "cpcv2_name"], "Unknown crop")
        geography = first_text(item, ["geographic_unit_name", "admin_1", "admin_0", "livelihood_zone_name"], "Unknown area")
        unit = first_text(item, ["unit_name", "unit"], "")
        value = first_text(item, ["description"], "")
        if not value:
            for key in ("value", "anomaly_percent", "percent_change", "production", "yield_value"):
                if item.get(key) not in (None, ""):
                    value = str(item.get(key))
                    break
        lines.append(f"{crop}: {value or 'No value'}{(' ' + unit) if unit else ''} ({geography})")

    return {
        "level": 0,
        "levelText": "Crop production data",
        "riskScore": f"{len(latest)} records in latest period",
        "status": "Authenticated FEWS crop production snapshot",
        "latestPeriod": format_date_short(latest_date),
        "trend": "Latest authenticated FEWS NET snapshot",
        "adm1Summary": " | ".join(lines) if lines else "No crop production detail available",
        "url": f"{API_BASE}/cropproductionfacts/",
    }


def fetch_generic_records(session, endpoint, base_params, fallbacks=None, max_pages=2):
    attempts = [base_params] + list(fallbacks or [])
    for params in attempts:
        try:
            records = paged_get(session, endpoint, params, max_pages=max_pages)
            if records:
                return records
        except requests.RequestException:
            continue
    return []


def main():
    if len(sys.argv) < 2:
        print("❌ Error: Country argument is required")
        print("Usage: python fetch_fews_food_data.py <country>")
        sys.exit(1)

    username = os.getenv("FEWS_USERNAME")
    password = os.getenv("FEWS_PASSWORD")
    if not username or not password:
        print("❌ Missing FEWS_USERNAME and/or FEWS_PASSWORD environment variables")
        sys.exit(1)

    country_input = sys.argv[1]
    session = build_session(username, password)
    country = resolve_country(session, country_input)
    iso2 = country["iso2"]
    country_name = country["country"]

    phase_records = fetch_phase_records(session, iso2)
    pop_records = fetch_population_records(session, iso2)

    market_records = fetch_generic_records(
        session,
        "marketpricefacts",
        [("format", "json"), ("page_size", "500"), ("ordering", "-reporting_date"), ("country_code", iso2)],
    )
    trade_records = fetch_generic_records(
        session,
        "tradeflowquantityvalue",
        [("format", "json"), ("page_size", "300"), ("ordering", "-reporting_date"), ("origin_country_code", iso2)],
        fallbacks=[
            [("format", "json"), ("page_size", "300"), ("ordering", "-reporting_date"), ("destination_country_code", iso2)],
            [("format", "json"), ("page_size", "300"), ("ordering", "-reporting_date"), ("country_code", iso2)],
        ],
    )
    crop_records = fetch_generic_records(
        session,
        "cropproductionfacts",
        [("format", "json"), ("page_size", "300"), ("ordering", "-reporting_date"), ("country_code", iso2)],
    )

    payload = {
        "country": country_name,
        "iso2": iso2,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": "github_actions_fews_snapshot",
        "cards": {
            "phase": summarize_phase(phase_records, pop_records),
            "market": build_market_card(market_records),
            "trade": build_trade_card(trade_records),
            "crop": build_crop_card(crop_records),
        },
    }

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_filename = f"food_security_{slugify_country(country_input)}.json"
    output_path = os.path.join(script_dir, "../data", output_filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    print(f"✅ FEWS food security snapshot saved to {output_path}")


if __name__ == "__main__":
    main()