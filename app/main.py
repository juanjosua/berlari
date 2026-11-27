import hashlib
import os
import secrets
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request  # noqa: E402
from fastapi.responses import JSONResponse, RedirectResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from fastapi.templating import Jinja2Templates  # noqa: E402
from jinja2 import pass_context  # noqa: E402
from starlette.middleware.sessions import SessionMiddleware  # noqa: E402

from . import coach, db, i18n, service, strava  # noqa: E402
from .plan import DISTANCES_KM, build_plan, fmt_pace, plan_to_dicts  # noqa: E402

HERE = Path(__file__).parent
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")
# Strava echoes this back when we register the webhook; derived so there is nothing extra to configure.
VERIFY_TOKEN = hashlib.sha256(f"{os.environ['SECRET_KEY']}:strava-webhook".encode()).hexdigest()[:32]

app = FastAPI(title="Berlari")
app.add_middleware(SessionMiddleware, secret_key=os.environ["SECRET_KEY"],
                   https_only=BASE_URL.startswith("https"), max_age=60 * 60 * 24 * 30)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
def request_lang(request: Request) -> str:
    """Cookie (chosen in the header) > saved on the account > browser language > English."""
    lang = request.cookies.get("lang")
    if lang not in i18n.LANGS:
        uid = request.session.get("uid")
        lang = ((db.get_user(uid) or {}).get("lang") if uid else None) or i18n.pick(
            request.headers.get("accept-language", ""))
    return lang if lang in i18n.LANGS else "en"


def i18n_context(request: Request) -> dict:
    return {"lang": request_lang(request), "langs": i18n.LANGS,
            "is_admin": request.session.get("uid") in ADMIN_IDS}


templates = Jinja2Templates(directory=HERE / "templates", context_processors=[i18n_context])
templates.env.filters["pace"] = fmt_pace
templates.env.globals["t"] = pass_context(lambda ctx, s: i18n.t(s, ctx.get("lang", "en")))
templates.env.globals["ld"] = pass_context(lambda ctx, d, f: i18n.fmt_date(d, f, ctx.get("lang", "en")))
templates.env.globals["pt"] = pass_context(lambda ctx, s: i18n.plan_text(s, ctx.get("lang", "en")))
# Cache-buster for static links: Cloudflare caches /static for hours, file mtime changes on each deploy.
templates.env.globals["v"] = int((HERE / "static" / "style.css").stat().st_mtime)
db.init()


def login_url(request: Request) -> str:
    """Strava's brand rules want the Connect button to link straight to strava.com/oauth/authorize."""
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    return strava.authorize_url(f"{BASE_URL}/auth/callback", state)


def current_user(request: Request) -> dict | None:
    uid = request.session.get("uid")
    return db.get_user(uid) if uid else None


def parse_goal(minutes: str) -> int | None:
    """Goal time typed as whole minutes (phones show a number pad; no colon needed). Blank -> None."""
    minutes = minutes.strip()
    if not minutes:
        return None
    if not minutes.isdigit() or not 10 <= int(minutes) <= 600:
        raise ValueError("goal time must be in minutes, between 10 and 600 (e.g. 119 for 1:59)")
    return int(minutes) * 60


@app.get("/")
def home(request: Request):
    user = current_user(request)
    if not user:
        return templates.TemplateResponse(request, "home.html", {"login_url": login_url(request)})
    saved = db.get_plan(user["id"])
    if saved:
        return RedirectResponse("/plan")
    return RedirectResponse("/new")


@app.get("/auth/login")
def login(request: Request):
    return RedirectResponse(login_url(request))


@app.get("/auth/callback")
def callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error or not code or state != request.session.pop("oauth_state", None):
        return templates.TemplateResponse(request, "home.html", {
            "error": "Strava login was cancelled or failed. Try again.", "login_url": login_url(request)})
    tok = strava.exchange_code(code)
    request.session["uid"] = tok["athlete"]["id"]
    if request.cookies.get("lang") in i18n.LANGS:
        db.set_lang(tok["athlete"]["id"], request.cookies["lang"])
    return RedirectResponse("/")


# Strava athlete IDs allowed to open /admin (comma-separated), e.g. ADMIN_ATHLETE_IDS=12345,67890
ADMIN_IDS = {int(x) for x in os.environ.get("ADMIN_ATHLETE_IDS", "").replace(" ", "").split(",") if x.isdigit()}
STRAVA_CAPACITY = int(os.environ.get("STRAVA_ATHLETE_CAPACITY", "10"))


@app.get("/admin")
def admin(request: Request):
    user = current_user(request)
    if not user or user["id"] not in ADMIN_IDS:
        raise HTTPException(404)  # don't reveal that the page exists
    rows = db.athletes()
    return templates.TemplateResponse(request, "admin.html", {
        "user": user, "athletes": rows, "capacity": STRAVA_CAPACITY, "date": date,
        "msg": request.query_params.get("msg", "")[:120]})


@app.post("/admin/remove/{athlete_id}")
def admin_remove(request: Request, athlete_id: int):
    """Disconnect an athlete: revoke on Strava (frees a capacity slot) and delete all their data."""
    user = current_user(request)
    if not user or user["id"] not in ADMIN_IDS:
        raise HTTPException(404)
    if athlete_id == user["id"]:
        return RedirectResponse("/admin?msg=You+can't+remove+yourself+here", status_code=303)
    target = db.get_user(athlete_id)
    if target:
        try:
            strava.deauthorize(target)
        except Exception:
            service.log.exception("Strava deauthorize failed for %s", athlete_id)  # still delete our copy
        db.delete_user(athlete_id)
    return RedirectResponse(f"/admin?msg=Removed+{(target or {}).get('name') or athlete_id}", status_code=303)


@app.get("/support")
def support(request: Request):
    page = "support_id.html" if request_lang(request) == "id" else "support.html"
    return templates.TemplateResponse(request, page, {"user": current_user(request)})


@app.post("/lang/{code}")
def set_language(request: Request, background: BackgroundTasks, code: str, next: str = Form("/")):
    if code not in i18n.LANGS:
        raise HTTPException(404)
    if not next.startswith("/") or next.startswith("//"):
        next = "/"  # only redirect within this site
    user = current_user(request)
    if user and service.change_language(user["id"], code):
        background.add_task(service.refresh_summary, user["id"], force=True)
        background.add_task(service.ensure_notes, user["id"])
    resp = RedirectResponse(next, status_code=303)
    resp.set_cookie("lang", code, max_age=60 * 60 * 24 * 365, samesite="lax",
                    secure=BASE_URL.startswith("https"))
    return resp


@app.get("/privacy")
def privacy(request: Request):
    page = "privacy_id.html" if request_lang(request) == "id" else "privacy.html"
    return templates.TemplateResponse(request, page, {"user": current_user(request)})


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
def create_plan(request: Request, background: BackgroundTasks, event_date: str = Form(...),
                distance: str = Form(...), runs_per_week: int = Form(4), goal_minutes: str = Form("")):
    user = current_user(request)
    if not user:
        return RedirectResponse("/", status_code=303)
    try:
        goal_s = parse_goal(goal_minutes)
        runs = strava.recent_runs(user)
        stats = strava.stats_from_runs(runs)
        days = build_plan(stats, distance, date.fromisoformat(event_date), runs_per_week, goal_s)
    except ValueError as e:
        return templates.TemplateResponse(request, "new.html", {
            "user": user, "distances": DISTANCES_KM, "error": str(e)}, status_code=400)
    params = {"event_date": event_date, "distance": distance,
              "runs_per_week": runs_per_week,
              "goal_time": f"{goal_s // 3600}:{goal_s // 60 % 60:02d}" if goal_s else ""}
    db.save_plan(user["id"], params, stats.__dict__, plan_to_dicts(days))
    service.seed_activities(user["id"], runs)
    background.add_task(service.refresh_summary, user["id"], force=True)
    background.add_task(service.ensure_notes, user["id"])
    return RedirectResponse("/plan", status_code=303)


@app.get("/plan")
def show_plan(request: Request, background: BackgroundTasks):
    user = current_user(request)
    if not user:
        return RedirectResponse("/")
    saved = db.get_plan(user["id"])
    if not saved:
        return RedirectResponse("/new")
    t = service.today()
    monday = (t - timedelta(days=t.weekday())).isoformat()
    days = [d for d in service.days_with_runs(user["id"], saved) if d["date"] >= monday]
    soon = {t.isoformat(), (t + timedelta(days=1)).isoformat()}
    if any(not d.get("why") for d in days if d["date"] in soon):
        background.add_task(service.ensure_notes, user["id"])  # safety net if the nightly job hasn't run yet
    weeks: list[list[dict]] = []
    for d in days:
        if not weeks or date.fromisoformat(d["date"]).weekday() == 0:
            weeks.append([])
        weeks[-1].append(d)
    return templates.TemplateResponse(request, "plan.html", {
        "user": user, "plan": saved, "weeks": weeks, "today": t.isoformat(), "coach_on": coach.enabled(),
        "summary": db.get_summary(user["id"]), "m": service.current_metrics(user["id"], saved),
        "chart": service.chart(user["id"], saved), "recent": service.recent_runs(user["id"]),
        "date": date, "days_left": (date.fromisoformat(saved["params"]["event_date"]) - t).days})


# --- Strava webhook: https://developers.strava.com/docs/webhooks/ ---

@app.get("/strava/webhook")
def webhook_verify(request: Request):
    q = request.query_params
    if q.get("hub.verify_token") != VERIFY_TOKEN:
        return JSONResponse({"error": "bad token"}, status_code=403)
    return {"hub.challenge": q.get("hub.challenge")}


@app.post("/strava/webhook")
async def webhook_event(request: Request, background: BackgroundTasks):
    background.add_task(service.handle_event, await request.json())
    return {"ok": True}  # Strava wants a 200 within 2 seconds; real work happens in the background
