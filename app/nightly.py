"""Daily job (deploy/berlari-nightly.timer, 20:00 Asia/Jakarta): adjust upcoming days after missed or short runs,
write tomorrow's coach notes and refresh each runner's fitness summary if they trained since the last one. Run: python -m app.nightly"""
import time

from dotenv import load_dotenv

load_dotenv()

from . import db, service  # noqa: E402


def main() -> None:
    db.init()
    with db.conn() as c:
        uids = [r[0] for r in c.execute("SELECT user_id FROM plans")]
    for uid in uids:
        try:
            service.evaluate_phases(uid)
            service.adapt_plan(uid)  # before notes, so tomorrow's note describes the adjusted session
        except Exception:
            service.log.exception("adapt_plan failed for user %s", uid)
        service.ensure_notes(uid)
        service.refresh_summary(uid)
        time.sleep(5)  # spread calls under Groq's free tokens-per-minute cap


if __name__ == "__main__":
    main()
