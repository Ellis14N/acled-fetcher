import requests  # type: ignore
from datetime import datetime
from collections import defaultdict

# UNHCR Refugee Statistics API v1 (public endpoints)
UNHCR_API_BASE = "https://api.unhcr.org/population/v1"

# ISO 3166-1 alpha-3 country codes for supported countries
COUNTRY_ISO_CODES = {
    "mali": "MLI",
    "nigeria": "NGA",
    "sudan": "SDN",
    "chad": "TCD",
}


def get_country_iso_code(country_name):
    """Convert country name to ISO 3-letter code."""
    country_lower = country_name.lower().strip()
    
    if country_lower in COUNTRY_ISO_CODES:
        return COUNTRY_ISO_CODES[country_lower]
    
    # Try partial match
    for key, code in COUNTRY_ISO_CODES.items():
        if country_lower in key or key in country_lower:
            return code
    
    raise ValueError(f"Country '{country_name}' not supported. Use: {', '.join(COUNTRY_ISO_CODES.keys())}")


def fetch_population_data_by_country_of_asylum(country_iso_code):
    """
    Fetch displacement population data where country is asylum destination.
    
    This gets all refugees/IDPs/asylum seekers currently in the specified country,
    broken down by their country of origin.
    """
    try:
        url = f"{UNHCR_API_BASE}/population/"
        base_params = {
            "coa": country_iso_code,  # country of asylum (destination)
            "cf_type": "ISO",
            "limit": 1000,
        }

        all_records = []
        page = 1
        max_pages = 1

        while page <= max_pages:
            params = {**base_params, "page": page}
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            payload = response.json()
            items = payload.get("items", []) if isinstance(payload, dict) else []
            all_records.extend(items)

            max_pages = int(payload.get("maxPages", 1) or 1) if isinstance(payload, dict) else 1
            page += 1

        print(f"   → Retrieved {len(all_records)} displacement records")
        return all_records

    except requests.exceptions.RequestException as e:
        print(f"⚠️  API Error: {e}")
        return []


def to_int(value):
    """Safely convert API values to integers."""
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def aggregate_population_by_origin(records):
    """
    Aggregate displacement population by country of origin.
    
    Returns:
        dict: Summary totals and breakdown by origin
    """
    totals = {
        "refugees": 0,
        "asylum_seekers": 0,
        "idps": 0,
        "stateless": 0,
        "oip": 0
    }
    
    by_origin = defaultdict(lambda: {
        "refugees": 0,
        "asylum_seekers": 0,
        "idps": 0,
        "stateless": 0,
        "oip": 0,
        "total": 0
    })
    
    for record in records:
        origin = record.get("coo_name", "Unknown")
        
        refugees = to_int(record.get("refugees", 0))
        asylum_seekers = to_int(record.get("asylum_seekers", 0))
        idps = to_int(record.get("idps", 0))
        stateless = to_int(record.get("stateless", 0))
        oip = to_int(record.get("oip", 0))
        
        totals["refugees"] += refugees
        totals["asylum_seekers"] += asylum_seekers
        totals["idps"] += idps
        totals["stateless"] += stateless
        totals["oip"] += oip
        
        by_origin[origin]["refugees"] += refugees
        by_origin[origin]["asylum_seekers"] += asylum_seekers
        by_origin[origin]["idps"] += idps
        by_origin[origin]["stateless"] += stateless
        by_origin[origin]["oip"] += oip
        by_origin[origin]["total"] += refugees + asylum_seekers + idps + stateless + oip
    
    return totals, dict(by_origin)


def get_top_origin_countries(by_origin, top_n=10):
    """Get top 10 countries of origin by total displaced population."""
    ranked = [
        {
            "origin": origin,
            "refugees": data["refugees"],
            "asylum_seekers": data["asylum_seekers"],
            "idps": data["idps"],
            "stateless": data["stateless"],
            "oip": data["oip"],
            "total": data["total"]
        }
        for origin, data in by_origin.items()
        if data["total"] > 0
    ]
    
    ranked.sort(key=lambda x: x["total"], reverse=True)
    return ranked[:top_n]


def get_unhcr_displacement_data(country="Mali"):
    """
    Fetch and return structured displacement data for a specific country of asylum.
    
    Args:
        country: Country name (e.g., "Mali", "Nigeria", "Sudan", "Chad")
    
    Returns:
        dict: Structured summary with displacement metrics
    """
    print(f"🌍 Fetching UNHCR displacement data for: {country}")
    
    try:
        country_iso = get_country_iso_code(country)
        print(f"   → Country ISO code: {country_iso}")
    except ValueError as e:
        raise Exception(str(e))
    
    raw_records = fetch_population_data_by_country_of_asylum(country_iso)
    if not raw_records:
        raise Exception(f"❌ No displacement data found for {country}")
    
    totals, by_origin = aggregate_population_by_origin(raw_records)
    top_origins = get_top_origin_countries(by_origin)
    
    total_displaced = sum(totals.values())
    
    summary = {
        "country": country,
        "country_code": country_iso,
        "date_retrieved": datetime.now().isoformat(),
        "total_displaced": total_displaced,
        "population_types": totals,
        "top_origin_countries": top_origins,
        "raw_record_count": len(raw_records)
    }
    
    return summary


# =========================
# TEST BLOCK
# =========================

if __name__ == "__main__":
    import sys
    
    country = sys.argv[1] if len(sys.argv) > 1 else "Mali"
    
    print(f"=== UNHCR Displacement Data for {country} ===\n")
    
    try:
        data = get_unhcr_displacement_data(country)
        
        print("\n📊 Summary:")
        print(f"Total displaced: {data['total_displaced']:,}")
        
        print(f"\nPopulation types:")
        for pop_type, count in data['population_types'].items():
            if count > 0:
                print(f"  {pop_type.replace('_', ' ').title()}: {count:,}")
        
        print(f"\nTop {len(data['top_origin_countries'])} countries of origin:")
        for i, origin_data in enumerate(data['top_origin_countries'], 1):
            print(f"  {i}. {origin_data['origin']}: {origin_data['total']:,}")
        
        print(f"\n✅ Successfully retrieved data for {country}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
