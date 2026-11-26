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

- **Coach text** (optional, needs `GROQ_SECRET_KEY`): `app/coach.py` asks a Groq-hosted LLM to write a
  fitness summary, a one-line "why" for each day (two weeks ahead, one request per week), and a short review
  after each run. The plan itself stays rule-based; the LLM only explains numbers we computed.
  Only training numbers are sent, never names.
- **Automatic tracking**: a Strava webhook (`/strava/webhook`) tells us when a run is uploaded, edited or
  deleted. The run is attached to that day of the plan and the day is marked done / partly done / missed.
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
