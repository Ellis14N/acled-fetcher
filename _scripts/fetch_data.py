import os
import sys
import json
from acled_fetch import get_acled_security_summary, DEFAULT_DATE_FROM, DEFAULT_DATE_TO

# =========================
# Paths & Setup
# =========================

# Accept country as a command-line argument (required)
if len(sys.argv) < 2:
    print("❌ Error: Country argument is required")
    print("Usage: python fetch_data.py <country>")
    sys.exit(1)

country = sys.argv[1]

# Get the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Path to save risk_data.json (named per country)
output_filename = f"risk_data_{country.lower().replace(' ', '_')}.json"
output_path = os.path.join(script_dir, "../data", output_filename)

# Ensure the folder exists
os.makedirs(os.path.dirname(output_path), exist_ok=True)

# =========================
# Fetch ACLED Data
# =========================

print(f"=== Fetching ACLED Security Data: {country} ({DEFAULT_DATE_FROM} to {DEFAULT_DATE_TO}) ===")

try:
    # Fetches last 30 days of data for the given country
    risk_data = get_acled_security_summary(country=country)

    # =========================
    # Save JSON
    # =========================
    with open(output_path, "w") as f:
        json.dump(risk_data, f, indent=2)

    print(f"✅ Data saved to {output_path}")
    print(f"   Total Events: {risk_data['total_events']}")
    print(f"   Total Fatalities: {risk_data['total_fatalities']}")
    print(f"   Weeks: {len(risk_data['weekly'])}, Months: {len(risk_data['monthly'])}")

except Exception as e:
    print(f"❌ Failed to fetch ACLED data: {e}")