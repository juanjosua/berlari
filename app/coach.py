"""LLM coach text via Groq (OpenAI-compatible API). The plan itself stays rule-based in plan.py;
the LLM only explains numbers we already computed. Only training numbers are sent, never names."""
import json
import os

import httpx

URL = "https://api.groq.com/openai/v1/chat/completions"
SYSTEM = ("You are a friendly, concise running coach. Use only the numbers given; never invent data. "
          "Plain English, no markdown, no medical claims.")


def enabled() -> bool:
    return bool(os.environ.get("GROQ_SECRET_KEY"))


def _ask(prompt: str, data: dict) -> dict:
    r = httpx.post(URL, timeout=40, headers={"Authorization": f"Bearer {os.environ['GROQ_SECRET_KEY']}"}, json={
        "model": os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
        "reasoning_effort": "low",
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": f"{prompt}\n\nDATA:\n{json.dumps(data)}"}],
    })
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])


def fitness_summary(profile: dict, params: dict) -> str:
    return _ask(
        "Summarise this runner's current fitness in 3-4 sentences: volume, consistency, pace trend, "
        "longest run, and what it means for their target race. "
        'Return JSON {"summary": "..."}.',
        {"profile": profile, "target": params})["summary"]


def explain_week(days: list[dict], stats: dict, params: dict) -> dict[str, str]:
    out = _ask(
        "For each training day, write one sentence (max 25 words) explaining why this session is in the "
        "plan and how to approach it. For rest days explain why rest matters at that point. "
        'Return JSON {"YYYY-MM-DD": "sentence", ...} with one key per day.',
        {"days": [{k: d[k] for k in ("date", "kind", "km", "detail")} for d in days],
         "runner": stats, "target": params})
    return {k: str(v) for k, v in out.items()}


def review_session(day: dict, actual: dict, stats: dict, params: dict) -> str:
    return _ask(
        "Write a 2-3 sentence review of this completed run versus what was planned that day: "
        "what went well, anything to watch, and a tip for the next sessions. "
        'Return JSON {"review": "..."}.',
        {"planned": {k: day[k] for k in ("kind", "km", "detail")}, "actual": actual,
         "runner": stats, "target": params})["review"]
