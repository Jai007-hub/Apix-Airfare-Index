from datetime import date

import pytest
from fastapi.testclient import TestClient

from api.main import app
from db.database import get_db
from db.models import CityPair, IndexValue, ValidationResult


@pytest.fixture()
def client(db_session, monkeypatch):
    monkeypatch.setattr("api.main.init_db", lambda: None)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_routes_sorted_by_weight_desc(db_session, client):
    db_session.add_all(
        [
            CityPair(origin="DEL", destination="BOM", label="DEL-BOM", dgca_weight=0.22),
            CityPair(origin="MAA", destination="BLR", label="MAA-BLR", dgca_weight=0.05),
        ]
    )
    db_session.commit()

    resp = client.get("/api/v1/routes")
    assert resp.status_code == 200
    body = resp.json()
    assert [r["label"] for r in body] == ["DEL-BOM", "MAA-BLR"]


def test_index_endpoint_returns_series(db_session, client):
    db_session.add(IndexValue(frequency="daily", period_date=date(2026, 7, 1), apix_value=100.0, base_period_date=date(2026, 7, 1)))
    db_session.add(IndexValue(frequency="daily", period_date=date(2026, 7, 2), apix_value=104.5, base_period_date=date(2026, 7, 1)))
    db_session.commit()

    resp = client.get("/api/v1/index?frequency=daily")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["apix_value"] == 100.0


def test_index_endpoint_404_when_empty(client):
    resp = client.get("/api/v1/index?frequency=weekly")
    assert resp.status_code == 404


def test_validation_endpoint(db_session, client):
    db_session.add(ValidationResult(period_month=date(2026, 6, 1), apix_value_rebased=120.4, cpi_airfare_value=120.4, pct_diff=0.0))
    db_session.add(ValidationResult(period_month=date(2026, 7, 1), apix_value_rebased=110.5, cpi_airfare_value=118.7, pct_diff=-6.9))
    db_session.commit()

    resp = client.get("/api/v1/validation")
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_months_compared"] == 2
    assert body["mape_pct"] > 0


# -- validation window filter -------------------------------------------------


def _seed_validation_months(db_session, months):
    """months: {(year, month): (apix_rebased, cpi)}"""
    for (year, month), (apix, cpi) in months.items():
        db_session.add(
            ValidationResult(
                period_month=date(year, month, 1),
                apix_value_rebased=apix,
                cpi_airfare_value=cpi,
                pct_diff=(apix - cpi) / cpi * 100,
            )
        )
    db_session.commit()


def test_validation_window_narrows_the_comparison(db_session, client):
    _seed_validation_months(
        db_session,
        {
            (2025, 1): (100.0, 100.0),
            (2025, 2): (110.0, 100.0),
            (2025, 3): (120.0, 100.0),
        },
    )

    full = client.get("/api/v1/validation").json()
    narrow = client.get("/api/v1/validation?start=2025-03-01&end=2025-03-31").json()

    assert full["n_months_compared"] == 3
    assert narrow["n_months_compared"] == 1
    # March alone is 20% out; averaged with the other two it is 10%.
    assert round(narrow["mape_pct"], 1) == 20.0
    assert round(full["mape_pct"], 1) == 10.0


def test_a_narrow_window_is_not_re_anchored_to_look_perfect(db_session, client):
    """Re-rebasing to the window would force its first month to 0% error by
    construction, making any short window look flawless for arithmetic
    reasons. The stored whole-series rebasing is kept instead."""
    _seed_validation_months(
        db_session,
        {(2025, 1): (100.0, 100.0), (2025, 2): (115.0, 100.0)},
    )

    narrow = client.get("/api/v1/validation?start=2025-02-01&end=2025-02-28").json()

    assert narrow["n_months_compared"] == 1
    assert round(narrow["mape_pct"], 1) == 15.0  # not 0.0


def test_validation_reports_the_full_extent_even_when_filtered(db_session, client):
    """The picker needs the real bounds, not the bounds of whatever slice is
    currently loaded, or it would ratchet itself shut."""
    _seed_validation_months(
        db_session,
        {(2025, 1): (100.0, 100.0), (2025, 6): (110.0, 100.0)},
    )

    narrow = client.get("/api/v1/validation?start=2025-06-01&end=2025-06-30").json()

    assert narrow["available_start"] == "2025-01-01"
    assert narrow["available_end"] == "2025-06-30"
    assert narrow["window_start"] == "2025-06-01"


def test_correlation_is_withheld_when_a_window_has_one_point(db_session, client):
    """One point cannot have a correlation; reporting 0 or 1 would be a lie
    the page would then print in a headline stat."""
    _seed_validation_months(
        db_session,
        {(2025, 1): (100.0, 100.0), (2025, 2): (110.0, 105.0)},
    )

    narrow = client.get("/api/v1/validation?start=2025-02-01&end=2025-02-28").json()

    assert narrow["pearson_correlation"] is None
    assert narrow["directional_agreement"] is None
