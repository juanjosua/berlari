import os
import secrets
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Form, Request  # noqa: E402
from fastapi.responses import RedirectResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from fastapi.templating import Jinja2Templates  # noqa: E402
from starlette.middleware.sessions import SessionMiddleware  # noqa: E402

from . import db, strava  # noqa: E402
from .plan import DISTANCES_KM, build_plan, fmt_pace, plan_to_dicts  # noqa: E402

HERE = Path(__file__).parent
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")

app = FastAPI(title="Berlari")
app.add_middleware(SessionMiddleware, secret_key=os.environ["SECRET_KEY"],
                   https_only=BASE_URL.startswith("https"), max_age=60 * 60 * 24 * 30)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")
templates.env.filters["pace"] = fmt_pace
db.init()


def current_user(request: Request) -> dict | None:
    uid = request.session.get("uid")
    return db.get_user(uid) if uid else None


def parse_goal(s: str) -> int | None:
    """'1:59:00' or '25:00' -> seconds. Blank -> None."""
    s = s.strip()
    if not s:
        return None
    parts = [int(p) for p in s.split(":")]
    if not 2 <= len(parts) <= 3 or any(p < 0 for p in parts):
        raise ValueError("goal time must look like 25:00 or 1:59:00")
    secs = 0
    for p in parts:
        secs = secs * 60 + p
    return secs or None


@app.get("/")
def home(request: Request):
    user = current_user(request)
    if not user:
        return templates.TemplateResponse(request, "home.html")
    saved = db.get_plan(user["id"])
    if saved:
        return RedirectResponse("/plan")
    return RedirectResponse("/new")


@app.get("/auth/login")
def login(request: Request):
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    return RedirectResponse(strava.authorize_url(f"{BASE_URL}/auth/callback", state))


@app.get("/auth/callback")
def callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error or not code or state != request.session.pop("oauth_state", None):
        return templates.TemplateResponse(request, "home.html",
                                          {"error": "Strava login was cancelled or failed. Try again."})
    tok = strava.exchange_code(code)
    request.session["uid"] = tok["athlete"]["id"]
    return RedirectResponse("/")


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


@app.post("/forget")
def forget(request: Request):
    """Delete everything we store about the user."""
    user = current_user(request)
    if user:
        db.delete_user(user["id"])
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.get("/new")
def new_plan_form(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse("/")
    return templates.TemplateResponse(request, "new.html", {
        "user": user, "distances": DISTANCES_KM, "saved": db.get_plan(user["id"])})


@app.post("/new")
def create_plan(request: Request, event_date: str = Form(...), distance: str = Form(...),
                runs_per_week: int = Form(4), goal_time: str = Form("")):
    user = current_user(request)
    if not user:
        return RedirectResponse("/", status_code=303)
    try:
        goal_s = parse_goal(goal_time)
        stats = strava.stats_from_runs(strava.recent_runs(user))
        days = build_plan(stats, distance, date.fromisoformat(event_date), runs_per_week, goal_s)
    except ValueError as e:
        return templates.TemplateResponse(request, "new.html", {
            "user": user, "distances": DISTANCES_KM, "error": str(e)}, status_code=400)
    params = {"event_date": event_date, "distance": distance,
              "runs_per_week": runs_per_week, "goal_time": goal_time}
    db.save_plan(user["id"], params, stats.__dict__, plan_to_dicts(days))
    return RedirectResponse("/plan", status_code=303)


@app.get("/plan")
def show_plan(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse("/")
    saved = db.get_plan(user["id"])
    if not saved:
        return RedirectResponse("/new")
    today = date.today().isoformat()
    days = [d for d in saved["days"] if d["date"] >= today]
    weeks: list[list[dict]] = []
    for d in days:
        if not weeks or date.fromisoformat(d["date"]).weekday() == 0:
            weeks.append([])
        weeks[-1].append(d)
    return templates.TemplateResponse(request, "plan.html", {
        "user": user, "plan": saved, "weeks": weeks, "today": today,
        "date": date, "days_left": (date.fromisoformat(saved["params"]["event_date"]) - date.today()).days})
