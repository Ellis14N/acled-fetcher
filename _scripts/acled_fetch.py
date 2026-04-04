import os
import requests
from dotenv import load_dotenv
from collections import Counter, defaultdict
from datetime import datetime, timedelta

# Load credentials
load_dotenv()

ACLED_EMAIL = os.getenv("ACLED_EMAIL")
ACLED_PASSWORD = os.getenv("ACLED_PASSWORD")

if not ACLED_EMAIL or not ACLED_PASSWORD:
    raise ValueError("❌ Please set ACLED_EMAIL and ACLED_PASSWORD in your .env file")

TOKEN_URL = "https://acleddata.com/oauth/token"
DATA_URL = "https://acleddata.com/api/acled/read"

EVENT_TYPES = [
    "Protests",
    "Explosions/Remote violence",
    "Battles",
    "Violence against civilians",
    "Riots",
    "Strategic developments"
]


def get_access_token():
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "username": ACLED_EMAIL,
        "password": ACLED_PASSWORD,
        "grant_type": "password",
        "client_id": "acled"
    }

    response = requests.post(TOKEN_URL, headers=headers, data=data)

    if response.status_code == 200:
        print("✅ ACLED access token obtained successfully")
        return response.json()["access_token"]
    else:
        raise Exception(f"❌ Token error: {response.status_code} - {response.text}")


def fetch_single_event_type(token, event_type, country, date_from, date_to):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    params = {
        "_format": "json",
        "country": country,
        "event_date": f"{date_from}|{date_to}",
        "event_date_where": "BETWEEN",
        "event_type": event_type,
        "limit": 5000,
        "fields": (
            "event_id_cnty|event_date|event_type|sub_event_type|"
            "fatalities|actor1|actor1_type|actor2|actor2_type|admin1|location"
        )
    }

    print(f"   → Fetching event data from ACLED")
    response = requests.get(DATA_URL, headers=headers, params=params)
    response.raise_for_status()

    print(f"   → Raw response: {response.text[:500]}")

    data = response.json()
    events = data.get("data", data) if isinstance(data, dict) else data

    print(f"   → {len(events)} events")
    return events


def fetch_all_event_types(country, date_from, date_to):
    token = get_access_token()
    all_events = []

    for etype in EVENT_TYPES:
        events = fetch_single_event_type(token, etype, country, date_from, date_to)
        all_events.extend(events)

    # Deduplicate
    unique_events = {}
    for e in all_events:
        unique_events[e["event_id_cnty"]] = e

    combined = list(unique_events.values())

    print("\n✅ Combined dataset:")
    print(f"   Raw events: {len(all_events)}")
    print(f"   Unique events: {len(combined)}")

    return combined


# =========================
# TIME SERIES BUILDERS
# =========================

def get_week_range(date_obj):
    """Return Monday–Sunday range for a given date."""
    start = date_obj - timedelta(days=date_obj.weekday())
    end = start + timedelta(days=6)
    return start, end


def build_weekly_series(events):
    ts = {}

    for e in events:
        date_str = e.get("event_date")
        if not date_str:
            continue

        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        start, end = get_week_range(date_obj)

        key = f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}"

        if key not in ts:
            ts[key] = {
                "events": 0,
                "fatalities": 0,
                "event_types": defaultdict(int)
            }

        ts[key]["events"] += 1
        ts[key]["fatalities"] += int(e.get("fatalities", 0))
        ts[key]["event_types"][e.get("event_type", "Unknown")] += 1

    for k in ts:
        ts[k]["event_types"] = dict(ts[k]["event_types"])

    return dict(sorted(ts.items()))


def build_monthly_series(events):
    ts = {}

    for e in events:
        date_str = e.get("event_date")
        if not date_str:
            continue

        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        key = date_obj.strftime("%Y-%m")

        if key not in ts:
            ts[key] = {
                "events": 0,
                "fatalities": 0,
                "event_types": defaultdict(int)
            }

        ts[key]["events"] += 1
        ts[key]["fatalities"] += int(e.get("fatalities", 0))
        ts[key]["event_types"][e.get("event_type", "Unknown")] += 1

    for k in ts:
        ts[k]["event_types"] = dict(ts[k]["event_types"])

    return dict(sorted(ts.items()))


def build_actor_summary(events, top_n=5):
    """Return the top N actors with their most frequent actor type."""
    counts = defaultdict(int)
    types = defaultdict(lambda: defaultdict(int))

    for e in events:
        for actor_field, type_field in [("actor1", "actor1_type"), ("actor2", "actor2_type")]:
            actor = e.get(actor_field)
            if not actor or not isinstance(actor, str):
                continue
            actor = actor.strip()
            if not actor or actor.lower() == "unknown":
                continue

            counts[actor] += 1
            actor_type = e.get(type_field) or "Unknown"
            actor_type = actor_type.strip() if isinstance(actor_type, str) else str(actor_type)
            if not actor_type:
                actor_type = "Unknown"
            types[actor][actor_type] += 1

    top_actors = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:top_n]
    summary = []
    for actor, count in top_actors:
        type_counts = types[actor]
        if type_counts:
            actor_type = sorted(type_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
        else:
            actor_type = "Unknown"
        summary.append({
            "actor": actor,
            "actor_type": actor_type,
            "count": count
        })

    return summary


# =========================
# PIPELINE WRAPPER FUNCTION
# =========================

def get_acled_security_summary(country="Mali"):
    """
    Returns structured SEC summary for the pipeline:
    - total events
    - total fatalities
    - weekly and monthly time series
    """
    date_from_str = "2024-10-01"   # Past 30 days approx
    date_to_str = "2024-12-31"     # Past 30 days approx

    print(f"📅 Date range: {date_from_str} → {date_to_str}")
    print(f"🌍 Country: {country}")

    events = fetch_all_event_types(country, date_from_str, date_to_str)

    monthly = build_monthly_series(events)
    latest_month_key = list(monthly.keys())[-1] if monthly else None
    recent_events = [e for e in events if e.get('event_date', '').startswith(latest_month_key)] if latest_month_key else []

    def build_filtered_actor_summary(events_local, top_n=5):
        counts = defaultdict(int)
        types = defaultdict(lambda: defaultdict(int))
        for e in events_local:
            for actor_field, type_field in [("actor1", "actor1_type"), ("actor2", "actor2_type")]:
                actor = e.get(actor_field)
                if not actor or not isinstance(actor, str) or actor.strip().lower() == "unknown" or "civilian" in actor.lower():
                    continue
                actor = actor.strip()
                counts[actor] += 1
                actor_type = e.get(type_field) or "Unknown"
                actor_type = actor_type.strip() if isinstance(actor_type, str) else str(actor_type)
                types[actor][actor_type] += 1
        top_actors = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:top_n]
        summary = []
        for actor, count in top_actors:
            type_counts = types[actor]
            actor_type = sorted(type_counts.items(), key=lambda item: (-item[1], item[0]))[0][0] if type_counts else "Unknown"
            summary.append({"actor": actor, "actor_type": actor_type, "count": count})
        return summary

    summary = {
        "country": country,
        "total_events": len(events),
        "total_fatalities": sum(int(e.get("fatalities", 0)) for e in events),
        "weekly": build_weekly_series(events),
        "monthly": monthly,
        "top_actors": build_actor_summary(events),  # Keep total for download
        "top_actors_recent": build_filtered_actor_summary(recent_events)  # Latest month, no civilians
    }

    return summary


# =========================
# TEST BLOCK
# =========================

if __name__ == "__main__":
    import sys

    country = sys.argv[1] if len(sys.argv) > 1 else "Mali"
    date_from_str = "2025-01-01"   # TEMP TEST
    date_to_str = "2025-04-02"     # TEMP TEST

    print(f"=== ACLED {country} Time-Series (temp test range) ===")
    print(f"📅 {date_from_str} → {date_to_str}")

    events = fetch_all_event_types(country, date_from_str, date_to_str)

    if events:
        print("\n📊 Building WEEKLY time series...")
        weekly_ts = build_weekly_series(events)

        print("\n📊 Building MONTHLY time series...")
        monthly_ts = build_monthly_series(events)

        print("\n=== WEEKLY OUTPUT ===")
        for k, v in weekly_ts.items():
            print(k, v)

        print("\n=== MONTHLY OUTPUT ===")
        for k, v in monthly_ts.items():
            print(k, v)
        print("\n=== TOP 5 ACTORS ===")
        top_actors = build_actor_summary(events)
        print(f"{'Actor':<40} {'Actor Type':<30} {'Count':>5}")
        print("-" * 80)
        for row in top_actors:
            print(f"{row['actor']:<40} {row['actor_type']:<30} {row['count']:>5}")
    else:
        print("No events returned.")
