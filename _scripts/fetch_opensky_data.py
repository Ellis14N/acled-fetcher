import os
import json
import argparse
from _scripts.opensky_fetch import get_opensky_summary


def main():
    parser = argparse.ArgumentParser(description="Fetch and save OpenSky summary data")
    parser.add_argument("--airport", type=str, required=True, help="ICAO airport code")
    parser.add_argument("--days-back", type=int, default=7, help="Days back to fetch")

    args = parser.parse_args()
    airport = args.airport.upper().strip()
    days_back = min(max(args.days_back, 1), 14)

    print(f"Starting OpenSky fetch: airport={airport}, days_back={days_back}")

    summary = get_opensky_summary(airport_code=airport, days_back=days_back)

    filename = f"data/opensky_{summary['airport'].lower().replace(' ', '_')}_{summary['total_flights']}.json"
    os.makedirs("data", exist_ok=True)

    with open(filename, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"✅ OpenSky data saved to {filename}")


if __name__ == "__main__":
    main()
