"""Is the seeded database still in step with the basket in config?

`apix.db` is not tracked by git -- it is ~200MB of generated data -- so a
`git pull` that changes the basket leaves every machine holding a database
built from the *old* one. Nothing errors: the dashboard simply keeps showing
the routes it already had, which looks exactly like "the update didn't work".

The launchers call this before starting, and reseed when it reports a
mismatch. Exit codes rather than output, so a shell can branch on it:

    0  in step, or no database yet (the launcher seeds that case anyway)
    1  out of step -- reseed
    2  could not tell (no database file, import failure); caller decides
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    try:
        from db.database import SessionLocal
        from db.models import CityPair
        from scraper.config import ROUTES
    except Exception as exc:  # pragma: no cover - environment problem, not logic
        print(f"could not check the basket: {exc}")
        return 2

    expected = {r.label for r in ROUTES}

    try:
        with SessionLocal() as session:
            actual = {r.label for r in session.query(CityPair).all()}
    except Exception as exc:  # pragma: no cover - unreadable/absent database
        print(f"could not read the database: {exc}")
        return 2

    if not actual:
        return 0  # nothing seeded yet; the caller's own check handles that

    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if not missing and not extra:
        return 0

    if missing:
        print(f"  routes in config but not in the database: {', '.join(missing)}")
    if extra:
        print(f"  routes in the database but no longer in config: {', '.join(extra)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
