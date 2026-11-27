"""LLM coach text via Groq (OpenAI-compatible API). The plan itself stays rule-based in plan.py;
the LLM only explains numbers we already computed. Only training numbers are sent, never names."""
import json
import os
import time

import httpx

URL = "https://api.groq.com/openai/v1/chat/completions"
LANG_ID = (" Write every text value in natural, friendly Bahasa Indonesia (use 'kamu'); keep JSON keys, "
           "dates and running terms like pace, tempo, interval in their usual form.")
SYSTEM = ("You are a friendly, concise running coach. Use only the numbers given; never invent data. "
          "Plain English, no markdown, no medical claims.")


def enabled() -> bool:
    return bool(os.environ.get("GROQ_SECRET_KEY"))


def _ask(prompt: str, data: dict, lang: str = "en") -> dict:
    r = httpx.post(URL, timeout=40, headers={"Authorization": f"Bearer {os.environ['GROQ_SECRET_KEY']}"}, json={
        "model": os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
        "reasoning_effort": "low",
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": SYSTEM + (LANG_ID if lang == "id" else "")},
                     {"role": "user", "content": f"{prompt}\n\nDATA:\n{json.dumps(data)}"}],
    })
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])


def _ask_with_retry(prompt: str, data: dict, lang: str = "en") -> dict:
    """Free tier has a tokens-per-minute cap; wait and retry when Groq says 429."""
    for attempt in range(3):
        try:
            return _ask(prompt, data, lang)
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 429 or attempt == 2:
                raise
            time.sleep(min(float(e.response.headers.get("retry-after", 20)), 60))


FITNESS_GLOSSARY = ("fitness = 42-day training load average (higher = fitter); fatigue = 7-day average; "
                    "form = fitness minus fatigue (negative = tired, positive = fresh). "
                    "metres_per_heartbeat = distance per heartbeat at running effort (higher = more efficient).")


def daily_summary(metrics: dict, recent_runs: list[dict], params: dict, previous: str | None,
                  lang: str = "en") -> dict:
    """Structured so the page can lay it out: headline, what got better, what to watch, next days."""
    out = _ask_with_retry(
        "Describe this runner's current physical condition, comparing with yesterday, last week and four weeks "
        "ago. Use the change_vs_* entries for directions (never recompute them) plus weekly km, longest run and "
        "heart-rate efficiency if present. Explain what the changes mean for their body (aerobic base, "
        "endurance, recovery). Be honest and kind: a single day changes little. Consider days_to_race "
        "(taper only in the final 1-3 weeks). The exact numbers are already shown next to your text, so do NOT "
        "copy the change strings, avoid parentheses, and use at most one number per item. "
        f"Glossary: {FITNESS_GLOSSARY} "
        'Return JSON {"headline": "max 14 words, the one key takeaway, encouraging", '
        '"better": ["1-3 items, max 20 words each: what improved and what it means for the body"], '
        '"watch": ["0-2 items, max 20 words each: what to be careful about"], '
        '"next": "one sentence, max 25 words: what to do in the next few days"}.',
        {"metrics": metrics, "recent_runs": recent_runs, "target": params, "previous_summary": previous}, lang)

    def as_list(v):
        return [str(x) for x in v] if isinstance(v, list) else ([str(v)] if v else [])
    return {"headline": str(out.get("headline", "")), "better": as_list(out.get("better"))[:3],
            "watch": as_list(out.get("watch"))[:2], "next": str(out.get("next", ""))}


def explain_days(days: list[dict], context: dict, lang: str = "en") -> dict[str, str]:
    """One or two upcoming days, written the day before with what happened recently in mind."""
    out = _ask_with_retry(
        "For each upcoming training day, write 1-2 sentences (max 40 words): why this session is in the "
        "plan and how to approach it given how recent training went (missed or extra runs, pace vs plan, "
        "fatigue/form). For rest days explain why rest matters now. "
        f"Glossary: {FITNESS_GLOSSARY} "
        'Return JSON {"YYYY-MM-DD": "text", ...} with one key per upcoming day.',
        {"upcoming": [{k: d[k] for k in ("date", "kind", "km", "detail")} for d in days], **context}, lang)
    return {k: str(v) for k, v in out.items()}


def review_session(day: dict, actual: dict, context: dict, lang: str = "en") -> str:
    return _ask_with_retry(
        "Write a 2-3 sentence review of this completed run versus what was planned that day: "
        "what went well, anything to watch, and a tip for the next sessions. "
        f"Glossary: {FITNESS_GLOSSARY} "
        'Return JSON {"review": "..."}.',
        {"planned": {k: day[k] for k in ("kind", "km", "detail")}, "actual": actual, **context}, lang)["review"]
