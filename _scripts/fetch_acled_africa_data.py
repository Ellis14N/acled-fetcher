import json
import os
from datetime import datetime, timezone

from acled_fetch import EVENT_TYPES, get_acled_security_summary
from africa_countries import AFRICAN_COUNTRIES


def build_country_entry(summary):
    return {
        "country": summary["country"],
        "data_status": "data",
        "has_activity": int(summary["total_events"]) > 0,
        "total_events": int(summary["total_events"]),
        "total_fatalities": int(summary["total_fatalities"]),
        "event_type_totals": {
            event_type: int(summary.get("event_type_totals", {}).get(event_type, 0))
            for event_type in EVENT_TYPES
        },
        "top_actors_recent": summary.get("top_actors_recent", [])[:5],
        "top_actors": summary.get("top_actors", [])[:5],
    }


def build_continent_totals(country_summaries):
    totals = {
        "countries_processed": len(country_summaries),
        "total_events": 0,
        "total_fatalities": 0,
        "event_type_totals": {event_type: 0 for event_type in EVENT_TYPES},
    }

    for summary in country_summaries:
        totals["total_events"] += int(summary["total_events"])
        totals["total_fatalities"] += int(summary["total_fatalities"])
        for event_type in EVENT_TYPES:
            totals["event_type_totals"][event_type] += int(summary["event_type_totals"].get(event_type, 0))

    return totals


def build_rankings(country_summaries):
    active_countries = [item for item in country_summaries if item.get("has_activity")]
    by_events = sorted(active_countries, key=lambda item: (-item["total_events"], item["country"]))
    by_fatalities = sorted(active_countries, key=lambda item: (-item["total_fatalities"], item["country"]))

    return {
        "top_events": by_events[:10],
        "top_fatalities": by_fatalities[:10],
    }


def fetch_acled_africa_summary():
    countries = []
    failed_countries = []
    date_from = None
    date_to = None

    for country in AFRICAN_COUNTRIES:
        print(f"\n=== Fetching ACLED all-Africa country: {country} ===")
        try:
            summary = get_acled_security_summary(country=country)
            if date_from is None:
                date_from = summary.get("date_from")
            if date_to is None:
                date_to = summary.get("date_to")
            countries.append(build_country_entry(summary))
        except Exception as exc:
            print(f"❌ Failed for {country}: {exc}")
            failed_countries.append({"country": country, "error": str(exc)})

    countries.sort(key=lambda item: (-item["total_events"], item["country"]))
    countries_with_activity = sum(1 for item in countries if item.get("has_activity"))

    return {
        "scope": "africa",
        "source": "acled",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date_from": date_from,
        "date_to": date_to,
        "country_count": len(AFRICAN_COUNTRIES),
        "countries_succeeded": len(countries),
        "countries_processed": len(countries),
        "countries_with_activity": countries_with_activity,
        "countries_without_activity": len(countries) - countries_with_activity,
        "countries_failed": len(failed_countries),
        "is_complete": len(countries) == len(AFRICAN_COUNTRIES),
        "failed_countries": failed_countries,
        "continent_totals": build_continent_totals(countries),
        "rankings": build_rankings(countries),
        "countries": countries,
    }


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "../data", "acled_africa_data.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    summary = fetch_acled_africa_summary()

    with open(output_path, "w") as file_handle:
        json.dump(summary, file_handle, indent=2)

    print(f"\n✅ Africa-wide ACLED data saved to {output_path}")
    print(f"   Countries succeeded: {summary['countries_succeeded']}/{summary['country_count']}")
    print(f"   Total events: {summary['continent_totals']['total_events']}")
    print(f"   Total fatalities: {summary['continent_totals']['total_fatalities']}")