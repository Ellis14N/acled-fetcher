import json
import os
import re
import sys
from datetime import UTC, datetime

import requests


API_BASE = "https://fdw.fews.net/api"
TOKEN_URL = "https://fdw.fews.net/api-token-auth/"
PHASE_ENDPOINT = f"{API_BASE}/ipcphase/"
POPULATION_ENDPOINT = f"{API_BASE}/ipcpopulationsize/"
COUNTRY_ENDPOINT = f"{API_BASE}/country/"
MARKET_ENDPOINT = f"{API_BASE}/marketpricefacts/"
TRADE_ENDPOINT = f"{API_BASE}/tradeflowquantityvalue/"
CROP_ENDPOINT = f"{API_BASE}/cropproductionfacts/"


def log(message):
    print(f"[FEWS] {message}", flush=True)


def slugify_country(country_name):
    return re.sub(r"[^a-z0-9]+", "_", str(country_name or "").strip().lower()).strip("_")


def normalize_date(value):
    text = str(value or "").strip()
    if not text:
        return ""
    return text[:10]


def format_date_short(value):
    text = normalize_date(value)
    if not text:
        return "Unknown"
    try:
        return datetime.fromisoformat(text).strftime("%b %Y")
    except ValueError:
        return text


def format_period(start_value, end_value, fallback_value=None):
    start = normalize_date(start_value)
    end = normalize_date(end_value)
    if start and end and start != end:
        return f"{format_date_short(start)} - {format_date_short(end)}"
    if start:
        return format_date_short(start)
    if end:
        return format_date_short(end)
    return format_date_short(fallback_value)


def to_number(value):
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def phase_label(value, description=None):
    level = int(round(to_number(value)))
    descriptions = {
        1: "Minimal",
        2: "Stressed",
        3: "Crisis",
        4: "Emergency",
        5: "Famine/Catastrophe",
    }
    if level <= 0:
        return "Unavailable"
    return f"Phase {level} - {description or descriptions.get(level, 'Unavailable')}"


def phase_grouping_label(value):
    level = int(round(to_number(value)))
    if level >= 5:
        return "Phase 5 (Catastrophe/Famine)"
    if level >= 4:
        return "Phase 4+ (Emergency or worse)"
    if level >= 3:
        return "Phase 3+ (Crisis or worse)"
    if level >= 1:
        return "Phase 1-2 (Minimal to Stressed)"
    return "Phase unavailable"


def is_current_scenario(record):
    scenario_code = str(record.get("scenario") or "").upper()
    scenario_name = str(record.get("scenario_name") or "").lower()
    return scenario_code == "CS" or "current" in scenario_name


def is_projection_scenario(record):
    scenario_code = str(record.get("scenario") or "").upper()
    scenario_name = str(record.get("scenario_name") or "").lower()
    return scenario_code.startswith("ML") or "projection" in scenario_name or "most likely" in scenario_name


def is_country_level(record, iso2):
    return str(record.get("fnid") or "").upper() == iso2.upper() or str(record.get("unit_type") or "").lower() == "admin0"


def is_subnational(record, iso2):
    return not is_country_level(record, iso2)


def record_sort_key(record):
    return (
        normalize_date(record.get("reporting_date")),
        normalize_date(record.get("projection_end")),
        to_number(record.get("preference_rating")),
    )


def choose_latest_record(records, predicate):
    matches = [record for record in records if predicate(record)]
    if not matches:
        return None
    matches.sort(key=record_sort_key, reverse=True)
    return matches[0]


def paged_get(session, endpoint_url, params, max_pages):
    results = []
    next_url = endpoint_url
    next_params = params
    for _ in range(max_pages):
        response = session.get(next_url, params=next_params, timeout=60)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            results.extend(payload)
            break
        if not isinstance(payload, dict):
            break
        page_rows = payload.get("results") or []
        results.extend(page_rows)
        next_url = payload.get("next")
        next_params = None
        if not next_url:
            break
    return results


def build_session(username, password):
    response = requests.post(
        TOKEN_URL,
        data={"username": username, "password": password},
        timeout=30,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        if response.status_code in (401, 403):
            raise RuntimeError(
                "FEWS authentication failed. Check the FEWS_username and FEWS_password repository secrets."
            ) from exc
        raise

    token = response.json()["token"]
    session = requests.Session()
    session.headers.update({"Authorization": "JWT " + token})
    return session


def resolve_country(session, country_input):
    query = str(country_input or "").strip()
    if not query:
        raise RuntimeError("Country input is required")

    log(f"Resolving country input: {query}")
    rows = paged_get(session, COUNTRY_ENDPOINT, {"format": "json", "page_size": 500}, max_pages=1)
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
            return iso2, row.get("preferred_name") or row.get("country") or query
        if len(query) == 3 and iso3 == query.upper():
            return iso2, row.get("preferred_name") or row.get("country") or query
        if lower in names:
            return iso2, row.get("preferred_name") or row.get("country") or query

    for row in rows:
        name = str(row.get("preferred_name") or row.get("iso_en_name") or row.get("country") or "").lower()
        if lower and lower in name:
            return str(row.get("iso3166a2") or "").upper(), row.get("preferred_name") or row.get("country") or query

    raise RuntimeError(f"Could not resolve FEWS country code for '{country_input}'")


def fetch_country_phase_records(session, iso2):
    log(f"Fetching country-level phase records for {iso2}")
    return paged_get(
        session,
        PHASE_ENDPOINT,
        {
            "format": "json",
            "page_size": 100,
            "fnid": iso2,
        },
        max_pages=1,
    )


def fetch_recent_phase_records(session, iso2):
    log(f"Fetching recent phase records for {iso2}")
    return paged_get(
        session,
        PHASE_ENDPOINT,
        {
            "format": "json",
            "page_size": 500,
            "country_code": iso2,
            "ordering": "-reporting_date",
        },
        max_pages=8,
    )


def fetch_population_records(session, iso2):
    log(f"Fetching population records for {iso2}")
    return paged_get(
        session,
        POPULATION_ENDPOINT,
        {
            "format": "json",
            "page_size": 500,
            "country_code": iso2,
            "phase": "3+",
        },
        max_pages=2,
    )


def fetch_market_records(session, iso2):
    log(f"Fetching market price records for {iso2}")
    return paged_get(
        session,
        MARKET_ENDPOINT,
        {
            "format": "json",
            "page_size": 500,
            "country_code": iso2,
            "ordering": "-reporting_date",
        },
        max_pages=3,
    )


def fetch_trade_records(session, iso2):
    log(f"Fetching trade flow records for {iso2}")
    records = paged_get(
        session,
        TRADE_ENDPOINT,
        {
            "format": "json",
            "page_size": 300,
            "origin_country_code": iso2,
            "ordering": "-reporting_date",
        },
        max_pages=3,
    )
    if records:
        return records

    # Fallback: some rows are keyed as destination-side country.
    return paged_get(
        session,
        TRADE_ENDPOINT,
        {
            "format": "json",
            "page_size": 300,
            "destination_country_code": iso2,
            "ordering": "-reporting_date",
        },
        max_pages=3,
    )


def fetch_crop_records(session, iso2):
    log(f"Fetching crop production records for {iso2}")
    return paged_get(
        session,
        CROP_ENDPOINT,
        {
            "format": "json",
            "page_size": 300,
            "country_code": iso2,
            "ordering": "-reporting_date",
        },
        max_pages=3,
    )


def choose_latest_population_record(records, predicate):
    matches = [record for record in records if predicate(record)]
    if not matches:
        return None
    matches.sort(
        key=lambda record: (
            normalize_date(record.get("projection_end")),
            normalize_date(record.get("reporting_date")),
        ),
        reverse=True,
    )
    return matches[0]


def dedupe_impacted_areas(rows):
    deduped = {}
    for row in rows:
        name = str(row.get("geographic_unit_name") or "").strip()
        if not name:
            continue
        phase_value = int(round(to_number(row.get("value"))))
        if phase_value < 3:
            continue
        key = name.lower()
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = row
            continue
        existing_phase = int(round(to_number(existing.get("value"))))
        existing_pref = to_number(existing.get("preference_rating"))
        row_pref = to_number(row.get("preference_rating"))
        if phase_value > existing_phase or (phase_value == existing_phase and row_pref > existing_pref):
            deduped[key] = row

    areas = []
    for row in deduped.values():
        value = int(round(to_number(row.get("value"))))
        areas.append(
            {
                "name": str(row.get("geographic_unit_name") or "Unknown area"),
                "phase_value": value,
                "phase_label": phase_label(value, row.get("description")),
                "unit_type": row.get("unit_type"),
            }
        )

    areas.sort(key=lambda item: (-item["phase_value"], item["name"]))
    return areas


def build_area_snapshot(records, iso2, predicate):
    matches = [
        record
        for record in records
        if predicate(record)
        and is_subnational(record, iso2)
        and str(record.get("unit_type") or "").lower() in {"admin1", "fsc_admin", "fsc_admin_lhz"}
    ]
    if not matches:
        return {
            "reporting_date": None,
            "period_label": "Unavailable",
            "impacted_areas": [],
        }

    latest_date = max(normalize_date(record.get("reporting_date")) for record in matches)
    latest_rows = [record for record in matches if normalize_date(record.get("reporting_date")) == latest_date]
    first_row = latest_rows[0]

    return {
        "reporting_date": latest_date,
        "period_label": format_period(
            first_row.get("projection_start"),
            first_row.get("projection_end"),
            first_row.get("reporting_date"),
        ),
        "impacted_areas": dedupe_impacted_areas(latest_rows),
    }


def format_population_label(population_record):
    if not population_record:
        return "Population estimate unavailable"
    people = int(round(to_number(population_record.get("value"))))
    population_range = str(population_record.get("population_range") or population_record.get("description") or "").strip()
    if people > 0 and population_range:
        return f"{people:,} people ({population_range})"
    if people > 0:
        return f"{people:,} people"
    if population_range:
        return population_range
    return "Population estimate unavailable"


def build_snapshot_section(title, phase_record, population_record, area_snapshot):
    phase_value = int(round(to_number((phase_record or {}).get("value")))) if phase_record else None
    phase_text = phase_label(phase_value, (phase_record or {}).get("description")) if phase_record else "Unavailable"
    impacted_areas = area_snapshot.get("impacted_areas") or []
    return {
        "title": title,
        "phase_value": phase_value,
        "phase_label": phase_text,
        "phase_date": normalize_date((phase_record or {}).get("reporting_date")),
        "phase_period": format_period(
            (phase_record or {}).get("projection_start"),
            (phase_record or {}).get("projection_end"),
            (phase_record or {}).get("reporting_date"),
        ) if phase_record else "Unavailable",
        "population_value": int(round(to_number((population_record or {}).get("value")))) if population_record else None,
        "population_label": format_population_label(population_record),
        "population_period": format_period(
            (population_record or {}).get("projection_start"),
            (population_record or {}).get("projection_end"),
            (population_record or {}).get("reporting_date"),
        ) if population_record else "Unavailable",
        "impacted_areas_period": area_snapshot.get("period_label") or "Unavailable",
        "impacted_area_count": len(impacted_areas),
        "impacted_areas": impacted_areas[:12],
    }


def pick_latest_date(records):
    dated = [normalize_date(r.get("reporting_date") or r.get("date")) for r in (records or [])]
    dated = [d for d in dated if d]
    return max(dated) if dated else ""


def summarize_market(records):
    if not records:
        return {
            "latest_period": "Unavailable",
            "commodity_count": 0,
            "highlights": [],
            "source": MARKET_ENDPOINT,
        }

    latest_date = pick_latest_date(records)
    latest_rows = [r for r in records if normalize_date(r.get("reporting_date") or r.get("date")) == latest_date]
    highlights = []
    for row in latest_rows[:10]:
        highlights.append(
            {
                "commodity": str(
                    row.get("commodity_name")
                    or row.get("indicator_name")
                    or row.get("cpcv2_name")
                    or row.get("commodity")
                    or "Unknown"
                ),
                "market": str(row.get("market_name") or row.get("market") or row.get("geographic_unit_name") or "Unknown"),
                "value": row.get("value"),
                "unit": row.get("unit") or row.get("unit_name") or row.get("currency") or None,
            }
        )

    return {
        "latest_period": format_date_short(latest_date),
        "commodity_count": len(latest_rows),
        "highlights": highlights,
        "source": MARKET_ENDPOINT,
    }


def summarize_trade(records):
    if not records:
        return {
            "latest_period": "Unavailable",
            "flow_count": 0,
            "highlights": [],
            "source": TRADE_ENDPOINT,
        }

    latest_date = pick_latest_date(records)
    latest_rows = [r for r in records if normalize_date(r.get("reporting_date") or r.get("date")) == latest_date]
    highlights = []
    for row in latest_rows[:10]:
        highlights.append(
            {
                "commodity": str(
                    row.get("commodity_name")
                    or row.get("indicator_name")
                    or row.get("cpcv2_name")
                    or row.get("commodity")
                    or "Unknown"
                ),
                "origin": str(row.get("origin_country_name") or row.get("origin_country") or "Unknown"),
                "destination": str(row.get("destination_country_name") or row.get("destination_country") or "Unknown"),
                "value": row.get("value") or row.get("quantity"),
                "unit": row.get("unit") or row.get("unit_name") or None,
            }
        )

    return {
        "latest_period": format_date_short(latest_date),
        "flow_count": len(latest_rows),
        "highlights": highlights,
        "source": TRADE_ENDPOINT,
    }


def summarize_crop(records):
    if not records:
        return {
            "latest_period": "Unavailable",
            "record_count": 0,
            "highlights": [],
            "source": CROP_ENDPOINT,
        }

    latest_date = pick_latest_date(records)
    latest_rows = [r for r in records if normalize_date(r.get("reporting_date") or r.get("date")) == latest_date]
    highlights = []
    for row in latest_rows[:10]:
        highlights.append(
            {
                "crop": str(
                    row.get("crop_name")
                    or row.get("commodity_name")
                    or row.get("indicator_name")
                    or row.get("cpcv2_name")
                    or "Unknown"
                ),
                "area": str(row.get("geographic_unit_name") or row.get("admin_1") or row.get("admin_0") or "Unknown"),
                "value": row.get("value") or row.get("production") or row.get("yield_value"),
                "unit": row.get("unit") or row.get("unit_name") or None,
            }
        )

    return {
        "latest_period": format_date_short(latest_date),
        "record_count": len(latest_rows),
        "highlights": highlights,
        "source": CROP_ENDPOINT,
    }


def build_output_payload(country_name, iso2, current_section, projection_section, market, trade, crop):
    current_phase_value = current_section.get("phase_value") or 0
    projection_phase_value = projection_section.get("phase_value") or 0
    summary_level = projection_phase_value or current_phase_value
    return {
        "country": country_name,
        "iso2": iso2,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source": "fews_api_github_actions",
        "summary_level": summary_level,
        "summary_label": phase_grouping_label(summary_level),
        "current": current_section,
        "projection": projection_section,
        "market_prices": market,
        "trade_flows": trade,
        "crop_production": crop,
        "url": PHASE_ENDPOINT,
    }


def main():
    if len(sys.argv) < 2:
        print("Error: country argument is required", file=sys.stderr)
        sys.exit(1)

    username = (os.getenv("FEWS_USERNAME") or "").strip()
    password = (os.getenv("FEWS_PASSWORD") or "").strip()
    if not username or not password:
        print("Error: missing FEWS_USERNAME and/or FEWS_PASSWORD", file=sys.stderr)
        sys.exit(1)

    country_input = sys.argv[1]
    session = build_session(username, password)
    iso2, country_name = resolve_country(session, country_input)
    log(f"Resolved {country_input} to {country_name} ({iso2})")

    admin0_phase_records = fetch_country_phase_records(session, iso2)
    recent_phase_records = fetch_recent_phase_records(session, iso2)
    population_records = fetch_population_records(session, iso2)
    market_records = fetch_market_records(session, iso2)
    trade_records = fetch_trade_records(session, iso2)
    crop_records = fetch_crop_records(session, iso2)

    current_phase = choose_latest_record(
        admin0_phase_records,
        lambda record: is_country_level(record, iso2) and is_current_scenario(record),
    )
    projection_phase = choose_latest_record(
        admin0_phase_records,
        lambda record: is_country_level(record, iso2) and is_projection_scenario(record),
    )

    current_population = choose_latest_population_record(
        population_records,
        lambda record: is_current_scenario(record) and str(record.get("phase") or "").startswith("3"),
    )
    projection_population = choose_latest_population_record(
        population_records,
        lambda record: is_projection_scenario(record) and str(record.get("phase") or "").startswith("3"),
    )

    current_areas = build_area_snapshot(recent_phase_records, iso2, is_current_scenario)
    projection_areas = build_area_snapshot(recent_phase_records, iso2, is_projection_scenario)

    current_section = build_snapshot_section("Current Situation", current_phase, current_population, current_areas)
    projection_section = build_snapshot_section("Forward Projection", projection_phase, projection_population, projection_areas)
    market_section = summarize_market(market_records)
    trade_section = summarize_trade(trade_records)
    crop_section = summarize_crop(crop_records)

    payload = build_output_payload(country_name, iso2, current_section, projection_section, market_section, trade_section, crop_section)

    output_filename = f"fews_snapshot_{slugify_country(country_input)}.json"
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", output_filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    log(f"Saved FEWS snapshot to {output_path}")


if __name__ == "__main__":
    main()