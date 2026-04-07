import json
import os
from datetime import datetime, timezone

import requests
import urllib3


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


DROUGHTWATCH_CANDIDATES = [
    "https://droughtwatch.icpac.net/api",
    "http://droughtwatch.icpac.net/api",
    "https://droughtwatch.icpac.net/eadw-api",
    "http://droughtwatch.icpac.net/eadw-api",
]

EA_HAZARDS_WATCH_CANDIDATES = [
    "https://eahazardswatch.icpac.net/api",
    "http://eahazardswatch.icpac.net/api",
]


def get_json(url):
    response = requests.get(
        url,
        headers={
            "Accept": "application/json,text/plain,*/*",
            "User-Agent": "acled-fetcher-icpac-snapshot/1.0",
        },
        timeout=60,
        verify=False,
        allow_redirects=True,
    )
    response.raise_for_status()
    return response.json()


def fetch_droughtwatch_catalog():
    """Fetch Droughtwatch API (drought, rainfall, temperature, vegetation, soil moisture)"""
    errors = []

    for base in DROUGHTWATCH_CANDIDATES:
        categories_url = f"{base}/categories/"
        datasets_url = f"{base}/datasets/"
        try:
            categories = get_json(categories_url)
            datasets = get_json(datasets_url)

            if not isinstance(categories, list) or not isinstance(datasets, list):
                raise ValueError("Categories/datasets response is not a JSON list")

            if not datasets:
                raise ValueError("Datasets list is empty")

            return {
                "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_base_url": base,
                "source_name": "droughtwatch",
                "category_count": len(categories),
                "dataset_count": len(datasets),
                "categories": categories,
                "datasets": datasets,
            }
        except Exception as exc:
            errors.append(f"{base}: {exc}")

    raise RuntimeError(f"Droughtwatch API failed: {'; '.join(errors)}")


def fetch_ea_hazards_watch_catalog():
    """Fetch EA Hazards Watch API (agricultural data, hazard warnings, disease outbreak)"""
    errors = []

    for base in EA_HAZARDS_WATCH_CANDIDATES:
        datasets_url = f"{base}/datasets"
        try:
            datasets = get_json(datasets_url)

            if not isinstance(datasets, list):
                raise ValueError("Datasets response is not a JSON list")

            if not datasets:
                raise ValueError("Datasets list is empty")

            # EA Hazards Watch doesn't have separate /categories/, so derive from datasets
            categories_set = set()
            for ds in datasets:
                if isinstance(ds, dict) and "category" in ds:
                    categories_set.add(ds["category"])

            categories = sorted(list(categories_set))

            return {
                "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_base_url": base,
                "source_name": "ea_hazards_watch",
                "category_count": len(categories),
                "dataset_count": len(datasets),
                "categories": categories,
                "datasets": datasets,
            }
        except Exception as exc:
            errors.append(f"{base}: {exc}")

    raise RuntimeError(f"EA Hazards Watch API failed: {'; '.join(errors)}")


def fetch_icpac_combined():
    """Fetch both ICPAC data sources (Droughtwatch + EA Hazards Watch)"""
    droughtwatch = fetch_droughtwatch_catalog()
    ea_hazards = fetch_ea_hazards_watch_catalog()

    return {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "droughtwatch": droughtwatch,
            "ea_hazards_watch": ea_hazards,
        },
    }


def main():
    snapshot = fetch_icpac_combined()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "..", "data", "icpac_droughtwatch_snapshot.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2)

    print("Saved ICPAC combined snapshot:", output_path)
    print("Droughtwatch API:", snapshot["sources"]["droughtwatch"]["source_base_url"])
    print("  Categories:", snapshot["sources"]["droughtwatch"]["category_count"])
    print("  Datasets:", snapshot["sources"]["droughtwatch"]["dataset_count"])
    print("EA Hazards Watch API:", snapshot["sources"]["ea_hazards_watch"]["source_base_url"])
    print("  Categories:", snapshot["sources"]["ea_hazards_watch"]["category_count"])
    print("  Datasets:", snapshot["sources"]["ea_hazards_watch"]["dataset_count"])


if __name__ == "__main__":
    main()
