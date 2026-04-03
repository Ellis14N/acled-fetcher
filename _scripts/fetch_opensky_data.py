import os
import json
import argparse
import sys
from pathlib import Path

# Allow executing from project root without package installation
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / '_scripts') not in sys.path:
    sys.path.insert(0, str(ROOT / '_scripts'))

from opensky_fetch import get_opensky_summary


def main():
    parser = argparse.ArgumentParser(description="Fetch and save OpenSky summary data")
    parser.add_argument("--airport", type=str, required=True, help="ICAO airport code")
    parser.add_argument("--days-back", type=int, default=7, help="Days back to fetch (max 7 for OpenSky API)")

    args = parser.parse_args()
    airport = args.airport.upper().strip()
    days_back = min(max(args.days_back, 1), 7)

    print(f"Starting OpenSky fetch: airport={airport}, days_back={days_back}")

    try:
        summary = get_opensky_summary(airport_code=airport, days_back=days_back)

        filename = f"data/opensky_{summary['airport'].lower().replace(' ', '_')}.json"
        os.makedirs("data", exist_ok=True)

        with open(filename, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"✅ OpenSky data saved to {filename}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ OpenSky fetch pipeline failed: {e}")
        raise


if __name__ == "__main__":
    main()
