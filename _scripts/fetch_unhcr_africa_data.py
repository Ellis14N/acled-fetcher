import json
import os
from datetime import datetime, timezone

from africa_countries import AFRICAN_COUNTRIES
from unhcr_fetch import NoDisplacementDataError, get_unhcr_displacement_data


POPULATION_TYPE_KEYS = ["refugees", "asylum_seekers", "idps", "stateless", "oip"]


def build_country_entry(summary):
    population_types = summary.get("population_types", {})
    return {
        "country": summary["country"],
        "country_code": summary.get("country_code"),
        "reference_year": summary.get("reference_year"),
        "data_status": "data",
        "total_displaced": int(summary.get("total_displaced", 0)),
        "population_types": {
            key: int(population_types.get(key, 0))
            for key in POPULATION_TYPE_KEYS
        },
        "top_origin_countries": summary.get("top_origin_countries", [])[:5],
        "trend": summary.get("trend", {}),
        "origin_country_count": int(summary.get("origin_country_count", 0)),
        "pagination_truncated": bool(summary.get("pagination_truncated", False)),
    }


def build_empty_country_entry(country):
    return {
        "country": country,
        "country_code": None,
        "reference_year": None,
        "data_status": "no_data",
        "total_displaced": 0,
        "population_types": {key: 0 for key in POPULATION_TYPE_KEYS},
        "top_origin_countries": [],
        "trend": {
            "basis": "yearly",
            "direction": "insufficient_data",
            "change": 0,
            "change_pct": None,
            "latest_year": None,
            "previous_year": None,
        },
        "origin_country_count": 0,
        "pagination_truncated": False,
    }


def build_continent_totals(country_summaries):
    totals = {
        "countries_processed": len(country_summaries),
        "total_displaced": 0,
        "population_types": {key: 0 for key in POPULATION_TYPE_KEYS},
    }

    for summary in country_summaries:
        totals["total_displaced"] += int(summary["total_displaced"])
        for key in POPULATION_TYPE_KEYS:
            totals["population_types"][key] += int(summary["population_types"].get(key, 0))

    return totals


def build_rankings(country_summaries):
    data_countries = [item for item in country_summaries if item.get("data_status") == "data"]
    by_displaced = sorted(data_countries, key=lambda item: (-item["total_displaced"], item["country"]))
    by_refugees = sorted(data_countries, key=lambda item: (-item["population_types"]["refugees"], item["country"]))

    return {
        "top_total_displaced": by_displaced[:10],
        "top_refugee_hosting": by_refugees[:10],
    }


def fetch_unhcr_africa_summary():
    countries = []
    failed_countries = []
    reference_years = set()

    for country in AFRICAN_COUNTRIES:
        print(f"\n=== Fetching UNHCR all-Africa country: {country} ===")
        try:
            summary = get_unhcr_displacement_data(country=country)
            if summary.get("reference_year"):
                reference_years.add(summary["reference_year"])
            countries.append(build_country_entry(summary))
        except NoDisplacementDataError:
            print(f"⚠️  No displacement data for {country}; recording zero totals")
            countries.append(build_empty_country_entry(country))
        except Exception as exc:
            error_message = str(exc)
            print(f"❌ Failed for {country}: {error_message}")
            failed_countries.append({"country": country, "error": error_message})

    countries.sort(key=lambda item: (-item["total_displaced"], item["country"]))
    countries_with_data = sum(1 for item in countries if item.get("data_status") == "data")
    countries_without_data = sum(1 for item in countries if item.get("data_status") == "no_data")
    truncated_countries = sum(1 for item in countries if item.get("pagination_truncated"))

    return {
        "scope": "africa",
        "source": "unhcr",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reference_year": min(reference_years) if len(reference_years) == 1 else None,
        "reference_years": sorted(reference_years),
        "country_count": len(AFRICAN_COUNTRIES),
        "countries_succeeded": countries_with_data,
        "countries_processed": len(countries),
        "countries_without_data": countries_without_data,
        "countries_failed": len(failed_countries),
        "countries_with_truncated_pagination": truncated_countries,
        "is_complete": len(countries) == len(AFRICAN_COUNTRIES),
        "failed_countries": failed_countries,
        "continent_totals": build_continent_totals(countries),
        "rankings": build_rankings(countries),
        "countries": countries,
    }


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "../data", "unhcr_africa_data.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    summary = fetch_unhcr_africa_summary()

    with open(output_path, "w") as file_handle:
        json.dump(summary, file_handle, indent=2)

    print(f"\n✅ Africa-wide UNHCR data saved to {output_path}")
    print(f"   Countries succeeded: {summary['countries_succeeded']}/{summary['country_count']}")
    print(f"   Total displaced: {summary['continent_totals']['total_displaced']:,}")