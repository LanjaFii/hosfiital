import pytest
from datetime import datetime, timedelta
from backend.app.db.session import SessionLocal, engine
from sqlalchemy import text
from backend.app.etl.kpis import calculate_daily_kpis


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_occupancy_rate_simple(db_session):
    # use a transaction to rollback test data
    conn = engine.connect()
    trans = conn.begin()
    try:
        # insert a service
        conn.execute(text("insert into services (id, code, name, created_at) values (9999, 'TST', 'Test Service', now())"))
        # capacity 10
        conn.execute(text("insert into service_capacity (service_id, as_of, beds_total) values (9999, now(), 10)"))
        # one snapshot with 3 occupied
        conn.execute(text("insert into occupancy_snapshots (service_id, snapshot_at, occupied_beds, available_beds) values (9999, now(), 3, 7)"))
        kpis = calculate_daily_kpis()
        assert any(k['occupied_beds_total'] >= 3 for k in kpis)
        # find the day of the snapshot
        today = (datetime.utcnow().date())
        day_k = [k for k in kpis if k['date'] == today]
        assert day_k, "expected KPI for today"
        rate = day_k[0]['occupancy_rate']
        assert rate is None or rate >= 0
    finally:
        trans.rollback()
        conn.close()


def test_budget_vs_expense(db_session):
    conn = engine.connect()
    trans = conn.begin()
    try:
        conn.execute(text("insert into services (id, code, name, created_at) values (9998, 'TST2', 'Test2', now())"))
        conn.execute(text("insert into budgets (service_id, year, budget_amount) values (9998, 2026, 10000)"))
        conn.execute(text("insert into expenses (service_id, period_start, amount) values (9998, now(), 2500)"))
        kpis = calculate_daily_kpis()
        # ensure expenses appear
        totals = [k['expenses_total'] for k in kpis if k['expenses_total'] > 0]
        assert totals, "expected some expense totals"
    finally:
        trans.rollback()
        conn.close()
