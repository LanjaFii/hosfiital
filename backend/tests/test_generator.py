import os
import sys
from datetime import datetime, timedelta

# ensure project root on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.generators.scenarios import run_scenario
from backend.app.db.session import SessionLocal
from sqlalchemy import text


def clear_and_run(scenario, days, seed):
    # run scenario with reset
    run_scenario(name=scenario, days=days, seed=seed, start_date=datetime.utcnow().date(), reset=True)


def test_reproducible_seed(tmp_path):
    days = 5
    seed = 123
    start = datetime.utcnow().date()
    run_scenario(name="normal", days=days, seed=seed, start_date=start, reset=True)
    # collect counts
    with SessionLocal() as s:
        res1 = s.execute(text("SELECT count(*) FROM admissions")).scalar()
    # run again with same seed and reset
    run_scenario(name="normal", days=days, seed=seed, start_date=start, reset=True)
    with SessionLocal() as s:
        res2 = s.execute(text("SELECT count(*) FROM admissions")).scalar()
    assert res1 == res2


def test_saturation_trend():
    days = 10
    seed = 7
    start = datetime.utcnow().date()
    run_scenario(name="saturation", days=days, seed=seed, start_date=start, reset=True)
    with SessionLocal() as s:
        # compute total occupied per day across services
        rows = s.execute(text("SELECT snapshot_at::date as d, sum(occupied_beds) as occ FROM occupancy_snapshots GROUP BY d ORDER BY d"))
        data = [(r[0], int(r[1])) for r in rows]
    counts = [c for _, c in data]
    assert len(counts) == days
    # trend should be non-decreasing overall (allow small fluctuations): check last > first
    assert counts[-1] >= counts[0]


def test_budget_overrun_trend():
    days = 10
    seed = 9
    start = datetime.utcnow().date()
    run_scenario(name="budget_overrun", days=days, seed=seed, start_date=start, reset=True)
    with SessionLocal() as s:
        rows = s.execute(text("SELECT period_start::date as d, sum(amount) as total FROM expenses GROUP BY d ORDER BY d"))
        data = [float(r[1]) for r in rows]
    assert len(data) == days
    # expense should increase overall
    assert data[-1] >= data[0]


def test_reset_clears_kpi_daily():
    start = datetime.utcnow().date()
    # seed data
    run_scenario(name="normal", days=3, seed=11, start_date=start, reset=True)
    # persist some daily KPIs (as the ETL pipeline would)
    from sqlalchemy import text as _text
    with SessionLocal() as s:
        s.execute(_text("INSERT INTO kpi_daily (day, admissions_total) VALUES (:d, 5) ON CONFLICT (day) DO NOTHING"), {"d": start})
        s.commit()
        assert s.execute(_text("SELECT count(*) FROM kpi_daily")).scalar() > 0
    # reset must wipe kpi_daily so stale days do not skew "dernier jour"
    run_scenario(name="normal", days=3, seed=12, start_date=start, reset=True)
    with SessionLocal() as s:
        rows = s.execute(_text("SELECT day FROM kpi_daily")).fetchall()
    assert rows == [], "kpi_daily must be cleared on reset"


def test_no_discharges_past_last_day():
    days = 10
    seed = 42
    start = datetime.utcnow().date()
    run_scenario(name="normal", days=days, seed=seed, start_date=start, reset=True)
    last_day = start + timedelta(days=days - 1)
    with SessionLocal() as s:
        # ensure no admission or discharge beyond last_day
        res = s.execute(text("SELECT max(admitted_at)::date, max(discharged_at)::date FROM admissions"))
        max_adm, max_dis = res.first()
    assert max_adm <= last_day
    assert max_dis <= last_day
