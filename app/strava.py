"""Strava OAuth + activity fetch. Docs: https://developers.strava.com/docs/"""
import os
import statistics
import time
from datetime import datetime, timedelta, timezone

import httpx

from . import db
from .plan import Stats, fmt_pace
from .sessions import ACTIVITY_TYPES, RUN_TYPES

AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
DEAUTH_URL = "https://www.strava.com/oauth/deauthorize"
API = "https://www.strava.com/api/v3"


def authorize_url(redirect_uri: str, state: str) -> str:
    params = {
        "client_id": os.environ["STRAVA_CLIENT_ID"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": "read,activity:read_all",
        "state": state,
    }
    return str(httpx.URL(AUTH_URL, params=params))


def _token_request(**data) -> dict:
    r = httpx.post(TOKEN_URL, data={
        "client_id": os.environ["STRAVA_CLIENT_ID"],
        "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
        **data,
    }, timeout=15)
    r.raise_for_status()
    return r.json()


def exchange_code(code: str) -> dict:
    """Returns token payload incl. 'athlete'. Saves the user."""
    tok = _token_request(code=code, grant_type="authorization_code")
    a = tok["athlete"]
    db.save_user(a["id"], f"{a.get('firstname', '')} {a.get('lastname', '')}".strip(),
                 tok["access_token"], tok["refresh_token"], tok["expires_at"])
    return tok


def access_token(user: dict) -> str:
    if user["expires_at"] > time.time() + 60:
        return user["access_token"]
    tok = _token_request(refresh_token=user["refresh_token"], grant_type="refresh_token")
    db.save_user(user["id"], user["name"], tok["access_token"], tok["refresh_token"], tok["expires_at"])
    return tok["access_token"]


def recent_runs(user: dict, weeks: int = 12) -> list[dict]:
    """Runs, walks and strength sessions (sessions.ACTIVITY_TYPES) from the last `weeks` weeks."""
    after = int((datetime.now(timezone.utc) - timedelta(weeks=weeks)).timestamp())
    headers = {"Authorization": f"Bearer {access_token(user)}"}
    runs, page = [], 1
    while True:
        r = httpx.get(f"{API}/athlete/activities", headers=headers,
                      params={"after": after, "per_page": 100, "page": page}, timeout=20)
        r.raise_for_status()
        batch = r.json()
        runs += [a for a in batch if a.get("sport_type", a.get("type")) in ACTIVITY_TYPES]
        if len(batch) < 100 or page >= 5:  # shortcut: caps at 500 activities, plenty for 12 weeks
            return runs
        page += 1




def get_activity(user: dict, activity_id: int) -> dict:
    r = httpx.get(f"{API}/activities/{activity_id}", timeout=20,
                  headers={"Authorization": f"Bearer {access_token(user)}"})
    r.raise_for_status()
    return r.json()


def run_summary(a: dict) -> dict:
    """The numbers we keep (and send to the coach) for one activity."""
    km = (a.get("distance") or 0) / 1000
    out = {"type": a.get("sport_type", a.get("type", "Run")), "km": round(km, 2),
           "moving_min": round(a["moving_time"] / 60, 1),
           "pace": fmt_pace(a["moving_time"] / km) if km else None,
           "elev_gain_m": a.get("total_elevation_gain")}
    if a.get("average_heartrate"):
        out |= {"avg_hr": round(a["average_heartrate"]), "max_hr": a.get("max_heartrate")}
    if a.get("splits_metric"):
        out["km_splits"] = [fmt_pace(s["moving_time"] / (s["distance"] / 1000))
                            for s in a["splits_metric"] if s.get("distance", 0) > 500]
    return out


def hr_stream(user: dict, activity_id: int) -> tuple[list, list] | None:
    """Heart rate and time samples for one activity, or None without HR data."""
    r = httpx.get(f"{API}/activities/{activity_id}/streams", timeout=20,
                  headers={"Authorization": f"Bearer {access_token(user)}"},
                  params={"keys": "heartrate,time", "key_by_type": "true"})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    data = r.json()
    if "heartrate" not in data:
        return None
    return data["heartrate"]["data"], data["time"]["data"]


def deauthorize(user: dict) -> None:
    """Revoke our access on Strava, which also frees the athlete's slot in the app's capacity."""
    r = httpx.post(DEAUTH_URL, data={"access_token": access_token(user)}, timeout=15)
    r.raise_for_status()


def subscribe_webhook(callback_url: str, verify_token: str) -> dict:
    """One-time: register our webhook with Strava (one subscription per app)."""
    r = httpx.post(f"{API}/push_subscriptions", timeout=30, data={
        "client_id": os.environ["STRAVA_CLIENT_ID"], "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
        "callback_url": callback_url, "verify_token": verify_token})
    return {"status": r.status_code, "body": r.json()}


def stats_from_runs(runs: list[dict]) -> Stats:
    """Summarise runs into the numbers the plan needs. Works with zero runs (beginner defaults)."""
    runs = [r for r in runs if r.get("sport_type", r.get("type", "Run")) in RUN_TYPES]
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=4)
    last4 = [r for r in runs if datetime.fromisoformat(r["start_date"].replace("Z", "+00:00")) >= cutoff]
    weekly_km = sum(r["distance"] for r in last4) / 1000 / 4
    longest = max((r["distance"] for r in runs), default=0) / 1000
    paces = [r["moving_time"] / (r["distance"] / 1000) for r in runs if r.get("distance", 0) > 1000]
    easy = statistics.median(paces) if paces else 420.0  # 7:00/km default
    return Stats(weekly_km=round(weekly_km, 1), longest_km=round(longest, 1), easy_pace_s=easy)
