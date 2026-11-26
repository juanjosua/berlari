"""Daily job (deploy/berlari-nightly.timer, 20:00 Asia/Jakarta): write tomorrow's coach notes and
refresh each runner's fitness summary if they trained since the last one. Run: python -m app.nightly"""
import time

from dotenv import load_dotenv

load_dotenv()

from . import db, service  # noqa: E402


def main() -> None:
    db.init()
    with db.conn() as c:
        uids = [r[0] for r in c.execute("SELECT user_id FROM plans")]
    for uid in uids:
        service.ensure_notes(uid)
        service.refresh_summary(uid)
        time.sleep(5)  # spread calls under Groq's free tokens-per-minute cap


if __name__ == "__main__":
    main()
