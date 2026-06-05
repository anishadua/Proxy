import os
from datetime import datetime, timedelta, timezone

import httpx

CAL_API = "https://api.cal.com/v2"


def _auth():
    return {"Authorization": f"Bearer {os.environ['CALCOM_API_KEY']}"}


def _tz():
    return os.getenv("CALCOM_TIMEZONE", "Asia/Kolkata")


def get_availability(args):
    days = int(args.get("days", 5))
    start = datetime.now(timezone.utc).date()
    end = start + timedelta(days=days)
    params = {
        "eventTypeId": int(os.environ["CALCOM_EVENT_TYPE_ID"]),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timeZone": _tz(),
    }
    headers = {**_auth(), "cal-api-version": "2024-09-04"}
    r = httpx.get(f"{CAL_API}/slots", params=params, headers=headers, timeout=30)
    if r.status_code != 200:
        return {"error": f"calendar unavailable ({r.status_code})"}
    data = r.json().get("data", {})
    slots = []
    if isinstance(data, dict):
        for day in sorted(data):
            for s in data[day]:
                slots.append(s["start"] if isinstance(s, dict) else s)
    return {"timezone": _tz(), "slots": slots[:6]}


def book_slot(args):
    body = {
        "start": args["start"],
        "eventTypeId": int(os.environ["CALCOM_EVENT_TYPE_ID"]),
        "attendee": {
            "name": args["name"],
            "email": args["email"],
            "timeZone": _tz(),
        },
    }
    headers = {**_auth(), "cal-api-version": "2024-08-13", "Content-Type": "application/json"}
    r = httpx.post(f"{CAL_API}/bookings", json=body, headers=headers, timeout=30)
    if r.status_code not in (200, 201):
        return {"error": f"could not book ({r.status_code})", "detail": r.text[:200]}
    data = r.json().get("data", {})
    return {
        "status": "confirmed",
        "uid": data.get("uid"),
        "start": data.get("start", args["start"]),
        "attendee": args["email"],
    }


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_availability",
            "description": "Get Anisha's real open interview slots from her calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "How many days ahead to search (default 5)"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_slot",
            "description": "Book a confirmed meeting in a slot returned by get_availability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {"type": "string", "description": "ISO start time of the chosen slot"},
                    "name": {"type": "string", "description": "Full name of the person booking"},
                    "email": {"type": "string", "description": "Email of the person booking"},
                },
                "required": ["start", "name", "email"],
            },
        },
    },
]

HANDLERS = {"get_availability": get_availability, "book_slot": book_slot}
