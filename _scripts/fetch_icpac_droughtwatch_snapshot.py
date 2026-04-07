import json
import os
from datetime import datetime, timezone

import requests
import urllib3


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


API_BASE_CANDIDATES = [
    "https://droughtwatch.icpac.net/api",
    "http://droughtwatch.icpac.net/api",
    "https://droughtwatch.icpac.net/eadw-api",
    "http://droughtwatch.icpac.net/eadw-api",
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


def fetch_icpac_catalog():
    errors = []

    for base in API_BASE_CANDIDATES:
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
                "category_count": len(categories),
                "dataset_count": len(datasets),
                "categories": categories,
                "datasets": datasets,
            }
        except Exception as exc:
            errors.append(f"{base}: {exc}")

    raise RuntimeError("; ".join(errors))


def main():
    snapshot = fetch_icpac_catalog()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "..", "data", "icpac_droughtwatch_snapshot.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2)

    print("Saved ICPAC snapshot:", output_path)
    print("Source:", snapshot["source_base_url"])
    print("Categories:", snapshot["category_count"])
    print("Datasets:", snapshot["dataset_count"])


if __name__ == "__main__":
    main()
