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
