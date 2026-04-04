import os
import sys
import json
from unhcr_fetch import get_unhcr_displacement_data

# =========================
# Paths & Setup
# =========================

# Accept country as a command-line argument (required)
if len(sys.argv) < 2:
    print("❌ Error: Country argument is required")
    print("Usage: python fetch_unhcr_data.py <country>")
    sys.exit(1)

country = sys.argv[1]

# Get the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Path to save unhcr_data.json (named per country)
output_filename = f"unhcr_data_{country.lower().replace(' ', '_')}.json"
output_path = os.path.join(script_dir, "../data", output_filename)

# Ensure the folder exists
os.makedirs(os.path.dirname(output_path), exist_ok=True)

# =========================
# Fetch UNHCR Data
# =========================

print(f"=== Fetching UNHCR Displacement Data: {country} ===")

try:
    # Fetches displacement data for the given country
    displacement_data = get_unhcr_displacement_data(country=country)

    # =========================
    # Save JSON
    # =========================
    with open(output_path, "w") as f:
        json.dump(displacement_data, f, indent=2)

    print(f"✅ Data saved to {output_path}")
    print(f"   Total displaced: {displacement_data['total_displaced']:,}")
    print(f"   Top origin countries: {len(displacement_data['top_origin_countries'])}")
    print(f"   Records processed: {displacement_data['raw_record_count']}")

except Exception as e:
    print(f"❌ Failed to fetch UNHCR data: {e}")
    sys.exit(1)
