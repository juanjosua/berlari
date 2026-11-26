# Berlari

Mobile-friendly web app that builds a **day-by-day running training plan** toward a target event,
based on your own Strava history.

1. Log in with Strava.
2. Pick your event: date, distance, optional goal time, runs per week.
3. Berlari reads your last 12 weeks of runs (weekly volume, longest run, typical pace)
   and generates a periodized plan (base → build → peak → taper) that starts from where you are now.

> *Berlari* means "to run" in Indonesian.

## Stack

Deliberately small so anyone can contribute:

- Python 3.12, [FastAPI](https://fastapi.tiangolo.com/), server-rendered Jinja2 templates
- Plain CSS (mobile-first), no JS build step
- SQLite (stdlib) for users and saved plans
- Strava OAuth2 + API v3 via `httpx`

```
app/
  main.py        routes (login, callback, plan form, plan view)
  strava.py      OAuth + activity fetching + token refresh
  plan.py        pure training-plan generator (no I/O, easy to test)
  coach.py       LLM coach text via Groq
  fitness.py     pure fitness/fatigue/form model
  service.py     shared glue: notes, summaries, webhook events
  nightly.py     daily job (coach notes + summaries)
  subscribe.py   one-time Strava webhook registration
  db.py          SQLite helpers
  templates/     Jinja2 pages
  static/        CSS
tests/           pytest tests for plan.py
deploy/          systemd unit + setup script for the VPS
```

## Run locally

1. Create a Strava API app at <https://www.strava.com/settings/api>.
   Set **Authorization Callback Domain** to `localhost` for local dev.
2. Copy the env file and fill in your values:

   ```bash
   cp .env.example .env
   ```

3. Install and run:

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

4. Open <http://localhost:8000>.

Run tests: `pip install pytest && pytest`

> Note: a new Strava API app only allows **1 connected athlete** (you) until Strava approves
> a capacity increase. Request one from the Strava API settings page before inviting friends.

## How the plan is built

`app/plan.py` is the heart of the project and is plain Python with no I/O:

- **Starting volume** = your average weekly km over the last 4 weeks (with a small floor).
- **Peak volume** depends on race distance, capped so weekly growth stays ≤ ~10%.
- Every 4th week is a **cutback** week (~80% volume).
- **Taper**: 1 week (5K/10K), 2 weeks (half), 3 weeks (marathon).
- Each week has one **long run**, one **quality session** (alternating intervals / tempo),
  and the rest **easy runs**; remaining days are rest.
- **Paces** come from your goal time if given, otherwise from your recent typical pace.

It is a heuristic, not coaching advice. Improvements welcome.

## AI coach and automatic tracking

- **Fitness numbers** (`app/fitness.py`, no LLM): each run gets a load score (running TSS from pace vs threshold).
  Fitness = 42-day average load, fatigue = 7-day average, form = fitness − fatigue. Shown on the plan page with
  the change since yesterday, plus weekly km, longest run and metres per heartbeat (aerobic efficiency).
- **Coach text** (optional, needs `GROQ_SECRET_KEY`, `app/coach.py`): the LLM only explains numbers we computed;
  only training numbers are sent, never names. Every result is saved, so page refreshes never call the LLM.
  - *Day notes*: written the evening before (today + tomorrow), using the last 7 days planned vs actual.
  - *Condition summary*: what changed vs yesterday / last week / four weeks ago. Regenerated at most once a day,
    only when runs changed since the last summary.
  - *Run review*: once per day, right after a run arrives.
- **Adaptive plan** (`plan.adapt`, rules, no LLM): each evening a long run missed yesterday moves to tomorrow
  (if there's room), a short week (<80%) trims this week's easy/long runs, and a very tired runner (form < -20)
  gets tomorrow's hard session swapped for an easy one. Never adds training. Changed days show an "Adjusted" label.
- **Nightly job** (`python -m app.nightly`, systemd timer at 20:00 Asia/Jakarta) writes tomorrow's notes and
  refreshes summaries.
- **Automatic tracking**: a Strava webhook (`/strava/webhook`) tells us when a run is uploaded, edited or deleted;
  runs are stored in `activities` and matched to plan days (done / partly done / missed / extra).
  Register the webhook once per Strava app: `python -m app.subscribe` (on the server, with `.env` filled).

## Contributing

1. Fork, create a branch, make your change.
2. Keep `plan.py` pure and add a test in `tests/` for any plan logic change.
3. Open a pull request with a short description.

Ideas: calendar (.ics) export, sync completed workouts back against the plan,
more event types (trail, ultra), Bahasa Indonesia translation.

## Deploy

See [`deploy/README.md`](deploy/README.md).

## License

MIT
