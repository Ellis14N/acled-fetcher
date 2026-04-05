import os
import requests
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime, timedelta

# Load credentials
load_dotenv()

ACLED_EMAIL = os.getenv("ACLED_EMAIL")
ACLED_PASSWORD = os.getenv("ACLED_PASSWORD")

TOKEN_URL = "https://acleddata.com/oauth/token"
DATA_URL = "https://acleddata.com/api/acled/read"
DEFAULT_DATE_FROM = os.getenv("ACLED_DATE_FROM", "2025-01-01")
DEFAULT_DATE_TO = os.getenv("ACLED_DATE_TO", "2025-02-01")

EVENT_TYPES = [
    "Protests",
    "Explosions/Remote violence",
    "Battles",
    "Violence against civilians",
    "Riots",
    "Strategic developments"
]


def safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def validate_acled_credentials():
    if ACLED_EMAIL and ACLED_PASSWORD:
        return

    if os.getenv("GITHUB_ACTIONS") == "true":
        raise ValueError("❌ Missing required GitHub Actions secrets: ACLED_EMAIL and/or ACLED_PASSWORD")

    raise ValueError("❌ Please set ACLED_EMAIL and ACLED_PASSWORD in your .env file")


def get_access_token():
    validate_acled_credentials()

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "username": ACLED_EMAIL,
        "password": ACLED_PASSWORD,
        "grant_type": "password",
        "client_id": "acled"
    }

    response = requests.post(TOKEN_URL, headers=headers, data=data, timeout=30)

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
    response = requests.get(DATA_URL, headers=headers, params=params, timeout=60)
    response.raise_for_status()

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
        event_id = e.get("event_id_cnty")
        if event_id:
            unique_events[event_id] = e

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
        ts[key]["fatalities"] += safe_int(e.get("fatalities", 0))
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
        ts[key]["fatalities"] += safe_int(e.get("fatalities", 0))
        ts[key]["event_types"][e.get("event_type", "Unknown")] += 1

    for k in ts:
        ts[k]["event_types"] = dict(ts[k]["event_types"])

    return dict(sorted(ts.items()))


def build_event_type_totals(events):
    """Count event types across all events in the selected date window."""
    totals = defaultdict(int)
    for e in events:
        totals[e.get("event_type", "Unknown")] += 1
    return dict(totals)


def build_actor_summary(events, top_n=5, exclude_civilians=False):
    """Return top actors counted by unique event participation."""
    actor_event_ids = defaultdict(set)
    actor_types = defaultdict(lambda: defaultdict(int))

    for e in events:
        event_id = e.get("event_id_cnty")
        if not event_id:
            continue

        # Ensure each actor is counted at most once per event even if it appears twice.
        actors_in_event = {}
        for actor_field, type_field in [("actor1", "actor1_type"), ("actor2", "actor2_type")]:
            actor = e.get(actor_field)
            if not actor or not isinstance(actor, str):
                continue

            actor = actor.strip()
            if not actor or actor.lower() == "unknown":
                continue
            if exclude_civilians and "civilian" in actor.lower():
                continue

            actor_type = e.get(type_field) or "Unknown"
            actor_type = actor_type.strip() if isinstance(actor_type, str) else str(actor_type)
            if not actor_type:
                actor_type = "Unknown"

            if actor not in actors_in_event:
                actors_in_event[actor] = actor_type

        for actor, actor_type in actors_in_event.items():
            actor_event_ids[actor].add(event_id)
            actor_types[actor][actor_type] += 1

    top_actors = sorted(
        ((actor, len(event_ids)) for actor, event_ids in actor_event_ids.items()),
        key=lambda item: item[1],
        reverse=True
    )[:top_n]

    summary = []
    for actor, count in top_actors:
        type_counts = actor_types[actor]
        actor_type = sorted(type_counts.items(), key=lambda item: (-item[1], item[0]))[0][0] if type_counts else "Unknown"
        summary.append({"actor": actor, "actor_type": actor_type, "count": count})

    return summary


# =========================
# PIPELINE WRAPPER FUNCTION
# =========================

def get_acled_security_summary(country="Mali", date_from=None, date_to=None):
    """
    Returns structured SEC summary for the pipeline:
    - total events
    - total fatalities
    - weekly and monthly time series
    """
    date_from_str = date_from or DEFAULT_DATE_FROM
    date_to_str = date_to or DEFAULT_DATE_TO

    print(f"📅 Date range: {date_from_str} → {date_to_str}")
    print(f"🌍 Country: {country}")

    events = fetch_all_event_types(country, date_from_str, date_to_str)

    monthly = build_monthly_series(events)

    summary = {
        "country": country,
        "date_from": date_from_str,
        "date_to": date_to_str,
        "total_events": len(events),
        "total_fatalities": sum(safe_int(e.get("fatalities", 0)) for e in events),
        "event_type_totals": build_event_type_totals(events),
        "weekly": build_weekly_series(events),
        "monthly": monthly,
        "top_actors": build_actor_summary(events),
        "top_actors_recent": build_actor_summary(events, exclude_civilians=True)
    }

    return summary


# =========================
# TEST BLOCK
# =========================

if __name__ == "__main__":
    import sys

    country = sys.argv[1] if len(sys.argv) > 1 else "Mali"
    date_from_str = DEFAULT_DATE_FROM
    date_to_str = DEFAULT_DATE_TO

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
