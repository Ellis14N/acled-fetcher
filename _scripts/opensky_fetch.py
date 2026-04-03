import os
import requests
from collections import defaultdict
from datetime import datetime, timedelta

# Load credentials from GitHub Secrets
OPENSKY_USERNAME = os.getenv("OPENSKY_USERNAME")
OPENSKY_PASSWORD = os.getenv("OPENSKY_PASSWORD")

if not OPENSKY_USERNAME or not OPENSKY_PASSWORD:
    raise ValueError("❌ Please set OPENSKY_USERNAME and OPENSKY_PASSWORD in GitHub Secrets")

# OpenSky API endpoints
OPENSKY_API_URL = "https://opensky-network.org/api"
STATES_ENDPOINT = f"{OPENSKY_API_URL}/states/all"
FLIGHTS_ENDPOINT = f"{OPENSKY_API_URL}/flights/all"

# Common airport codes and regions (African focus)
AIRPORT_CODES = {
    "HAAB": "Addis Ababa",
    "HKJK": "Nairobi",
    "FAOR": "Johannesburg",
    "FACT": "Cape Town",
    "DNMM": "Lagos",
    "DNAA": "Abuja",
    "DTTA": "Tunis",
    "GMMN": "Casablanca",
    "HUEN": "Entebbe",
    "HECA": "Cairo"
}


def get_opensky_auth():
    """Return authentication tuple for OpenSky API."""
    return (OPENSKY_USERNAME, OPENSKY_PASSWORD)


def fetch_aircraft_states(time_s=None):
    """
    Fetch current aircraft state vectors from OpenSky.
    
    Args:
        time_s (int): Unix timestamp, defaults to most recent data
    
    Returns:
        list: Aircraft state vectors
    """
    params = {}
    if time_s:
        params["time"] = time_s
    
    try:
        response = requests.get(
            STATES_ENDPOINT,
            auth=get_opensky_auth(),
            params=params,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        states = data.get("states", [])
        
        print(f"✅ OpenSky API response received")
        print(f"   → Status: {response.status_code}")
        print(f"   → Aircraft on ground/in air: {len(states)}")
        
        return states
    except requests.exceptions.RequestException as e:
        raise Exception(f"❌ OpenSky API error: {e}")


def fetch_flights_by_airport(airport_icao, begin, end):
    """
    Fetch departures and arrivals for a specific airport.
    
    Args:
        airport_icao (str): ICAO code for airport
        begin (int): Unix timestamp start
        end (int): Unix timestamp end
    
    Returns:
        tuple: (departures, arrivals)
    """
    try:
        # Fetch departures
        dep_response = requests.get(
            f"{OPENSKY_API_URL}/flights/departure",
            params={"airport": airport_icao, "begin": begin, "end": end},
            auth=get_opensky_auth(),
            timeout=30
        )
        if not dep_response.ok:
            raise Exception(f"❌ OpenSky departure fetch failed ({dep_response.status_code}): {dep_response.text}")
        departures = dep_response.json()
        
        # Fetch arrivals
        arr_response = requests.get(
            f"{OPENSKY_API_URL}/flights/arrival",
            params={"airport": airport_icao, "begin": begin, "end": end},
            auth=get_opensky_auth(),
            timeout=30
        )
        if not arr_response.ok:
            raise Exception(f"❌ OpenSky arrival fetch failed ({arr_response.status_code}): {arr_response.text}")
        arrivals = arr_response.json()
        
        print(f"🛫 {airport_icao}: {len(departures)} departures, {len(arrivals)} arrivals")
        
        return departures, arrivals
    except requests.exceptions.RequestException as e:
        raise Exception(f"❌ Error fetching airport data: {e}")


# =========================
# TIME SERIES BUILDERS
# =========================

def get_week_range(date_obj):
    """Return Monday–Sunday range for a given date."""
    start = date_obj - timedelta(days=date_obj.weekday())
    end = start + timedelta(days=6)
    return start, end


def build_weekly_series(flights):
    """Build weekly time series from flight data."""
    ts = {}
    
    for flight in flights:
        if not flight.get("firstSeen"):
            continue
        
        # Convert Unix timestamp to datetime
        date_obj = datetime.fromtimestamp(flight["firstSeen"])
        start, end = get_week_range(date_obj)
        
        key = f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}"
        
        if key not in ts:
            ts[key] = {
                "flights": 0,
                "aircraft_types": defaultdict(int)
            }
        
        ts[key]["flights"] += 1
        
        # Track aircraft type if available
        aircraft_type = flight.get("aircraft", "Unknown")
        ts[key]["aircraft_types"][aircraft_type] += 1
    
    for k in ts:
        ts[k]["aircraft_types"] = dict(ts[k]["aircraft_types"])
    
    return dict(sorted(ts.items()))


def build_monthly_series(flights):
    """Build monthly time series from flight data."""
    ts = {}
    
    for flight in flights:
        if not flight.get("firstSeen"):
            continue
        
        # Convert Unix timestamp to datetime
        date_obj = datetime.fromtimestamp(flight["firstSeen"])
        key = date_obj.strftime("%Y-%m")
        
        if key not in ts:
            ts[key] = {
                "flights": 0,
                "aircraft_types": defaultdict(int)
            }
        
        ts[key]["flights"] += 1
        
        # Track aircraft type if available
        aircraft_type = flight.get("aircraft", "Unknown")
        ts[key]["aircraft_types"][aircraft_type] += 1
    
    for k in ts:
        ts[k]["aircraft_types"] = dict(ts[k]["aircraft_types"])
    
    return dict(sorted(ts.items()))


# =========================
# PIPELINE WRAPPER FUNCTION
# =========================

def get_opensky_summary(airport_code="JFK", days_back=30):
    """
    Returns structured OpenSky summary for the pipeline:
    - total flights
    - departures/arrivals breakdown
    - weekly and monthly time series
    - aircraft type distribution
    
    Args:
        airport_code (str): ICAO airport code (e.g., "KJFK" for JFK)
        days_back (int): Number of days to look back
    
    Returns:
        dict: Structured summary with flights, weekly, monthly data
    """
    
    # Calculate time range
    end_time = int(datetime.now().timestamp())
    begin_time = end_time - (days_back * 86400)
    
    date_from_str = datetime.fromtimestamp(begin_time).strftime("%Y-%m-%d")
    date_to_str = datetime.fromtimestamp(end_time).strftime("%Y-%m-%d")
    
    print(f"📅 Date range: {date_from_str} → {date_to_str} ({days_back} days)")
    print(f"✈️ Airport: {airport_code}")
    
    try:
        departures, arrivals = fetch_flights_by_airport(airport_code, begin_time, end_time)
        
        all_flights = departures + arrivals
        
        summary = {
            "airport": airport_code,
            "region": AIRPORT_CODES.get(airport_code.replace("K", ""), "Unknown"),
            "total_flights": len(all_flights),
            "total_departures": len(departures),
            "total_arrivals": len(arrivals),
            "weekly": build_weekly_series(all_flights),
            "monthly": build_monthly_series(all_flights)
        }

        print(f"\n✅ OpenSky summary compiled:")
        print(f"   Total flights: {summary['total_flights']}")
        print(f"   Departures: {summary['total_departures']}")
        print(f"   Arrivals: {summary['total_arrivals']}")

        return summary

    except Exception as e:
        error_text = str(e)
        print(f"❌ Error building OpenSky summary: {error_text}")

        if "historical flights" in error_text.lower() or "cannot access historical" in error_text.lower():
            print("ℹ️ Falling back to live state data because historical flight access is not available")
            states = fetch_aircraft_states()
            summary = {
                "airport": airport_code,
                "region": AIRPORT_CODES.get(airport_code.replace("K", ""), "Unknown"),
                "total_flights": len(states),
                "total_departures": 0,
                "total_arrivals": 0,
                "weekly": {},
                "monthly": {}
            }
            return summary

        raise