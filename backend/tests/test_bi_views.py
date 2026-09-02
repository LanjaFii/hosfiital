from datetime import date, datetime, time
import json
from sqlalchemy import text
from backend.app.db.session import engine, SessionLocal
from scripts.generators.scenarios import run_scenario
from backend.app.models.models import Analysis, Recommendation, Service, ServiceCapacity


def setup_test_data():
    # populate DB with deterministic small dataset (reset=True)
    start = date(2026, 8, 1)
    run_scenario('normal', days=3, seed=42, start_date=start, reset=True)
    return start


def test_create_views_and_columns():
    # Read and execute each SQL view file
    sql_files = [
        'backend/db/bi_views/vw_kpi_daily.sql',
        'backend/db/bi_views/vw_service_summary.sql',
        'backend/db/bi_views/vw_budget_variance.sql',
        'backend/db/bi_views/vw_recommendations.sql',
        'backend/db/bi_views/vw_occupancy_timeseries.sql',
        'backend/db/bi_views/vw_activity_timeseries.sql',
        'backend/db/bi_views/vw_staff_activity.sql',
    ]
    with engine.begin() as conn:
        for fp in sql_files:
            with open(fp, 'r') as f:
                sql = f.read()
            # execute create or replace view
            conn.execute(text(sql))

    # verify columns exist by selecting zero rows (to get metadata)
    expected_columns = {
        'vw_kpi_daily': ['day', 'admissions_total', 'discharges_total', 'occupied_beds_total', 'capacity_total', 'occupancy_rate', 'expenses_total', 'energy_total'],
        'vw_service_summary': ['date', 'service_id', 'service_name', 'beds_total', 'occupied_beds', 'occupancy_rate', 'admissions', 'discharges', 'expenses', 'budget_amount', 'energy_kwh', 'staff_headcount'],
        'vw_budget_variance': ['service_id', 'service_name', 'year', 'budget_amount', 'expenses_amount', 'variance_abs', 'variance_pct'],
        'vw_recommendations': ['recommendation_id', 'analysis_id', 'service_id', 'service_name', 'rule_id', 'text', 'status', 'created_at', 'risk_level', 'triggered_by', 'triggered_at', 'kpi_snapshot', 'anomalies', 'severity', 'evidence'],
        'vw_occupancy_timeseries': ['snapshot_id', 'snapshot_at', 'date', 'hour', 'service_id', 'service_name', 'occupied_beds', 'available_beds', 'beds_total', 'occupancy_rate'],
        'vw_activity_timeseries': ['activity_id', 'period_start', 'period_end', 'date', 'service_id', 'service_name', 'admissions_count', 'discharges_count', 'visits_count', 'avg_los'],
        'vw_staff_activity': ['staff_level_id', 'as_of', 'date', 'service_id', 'service_name', 'role', 'headcount', 'fte', 'patients_per_fte'],
    }

    with engine.connect() as conn:
        for view, cols in expected_columns.items():
            res = conn.execute(text(f'SELECT * FROM {view} LIMIT 0'))
            keys = list(res.keys())
            for c in cols:
                assert c in keys, f"Column {c} missing in {view}, keys: {keys}"


def test_aggregations_and_zero_division_protection():
    start = setup_test_data()
    test_date = start
    with engine.begin() as conn:
        # ensure views exist
        with open('backend/db/bi_views/vw_service_summary.sql') as f:
            conn.execute(text(f.read()))
        with open('backend/db/bi_views/vw_activity_timeseries.sql') as f:
            conn.execute(text(f.read()))

        # compute sum of admissions from vw_service_summary and activity_records
        q1 = text("SELECT SUM(admissions) FROM vw_service_summary WHERE date = :d")
        q2 = text("SELECT SUM(admissions_count) FROM activity_records WHERE period_start::date = :d")
        s1 = conn.execute(q1, {'d': test_date}).scalar() or 0
        s2 = conn.execute(q2, {'d': test_date}).scalar() or 0
        assert int(s1) == int(s2), f"Sum mismatch admissions vw_service_summary({s1}) vs activity_records({s2})"

        # insert a capacity zero for one service to test division by zero handling
        session = SessionLocal()
        svc = session.query(Service).first()
        assert svc is not None, 'no service present'
        sid = svc.id
        # as_of must be on/before the queried date so this 0-capacity record is
        # the effective one for that day (capacity is a point-in-time as-of).
        # Use a later timestamp than the generator's record so it is the latest.
        sc = ServiceCapacity(service_id=sid, as_of=datetime.combine(test_date, time.max), beds_total=0, notes='test zero')
        session.add(sc)
        session.commit()
        session.close()

        # recreate view to pick up new capacity
        with open('backend/db/bi_views/vw_service_summary.sql') as f:
            conn.execute(text(f.read()))

        # check occupancy_rate is NULL for that service/date
        q = text("SELECT occupancy_rate FROM vw_service_summary WHERE date = :d AND service_id = :sid")
        val = conn.execute(q, {'d': test_date, 'sid': sid}).scalar()
        assert val is None, f"Expected NULL occupancy_rate when beds_total=0, got {val}"


def test_vw_recommendations_extracts_severity_and_evidence():
    # create an Analysis and Recommendation manually and verify view extracts severity and evidence
    session = SessionLocal()
    try:
        # create analysis with anomalies array containing matching rule
        anomalies = [
            {'rule_id': 'saturation_v1', 'status': 'triggered', 'severity': 'critical', 'values': {'service_issue': {'service_id': 1, 'occupancy_rate': 0.99}}}
        ]
        # ensure a service exists to satisfy FK on recommendations
        svc = session.query(Service).first()
        if svc is None:
            svc = Service(code='TST', name='Test Service')
            session.add(svc)
            session.flush()

        a = Analysis(triggered_by='test', triggered_at=datetime.utcnow(), kpi_snapshot={'admissions_total':1}, anomalies=anomalies, risk_level='critical')
        session.add(a)
        session.flush()
        # create recommendation referencing that rule
        r = Recommendation(analysis_id=a.id, service_id=svc.id, text='test rec', type='saturation_v1', status='open')
        session.add(r)
        session.commit()
        rid = r.id

        # ensure view exists
        with engine.begin() as conn:
            with open('backend/db/bi_views/vw_recommendations.sql') as f:
                conn.execute(text(f.read()))
            row = conn.execute(text('SELECT severity, evidence FROM vw_recommendations WHERE recommendation_id = :rid'), {'rid': rid}).fetchone()
            assert row is not None, 'vw_recommendations returned no row'
            mapping = row._mapping
            sev = mapping.get('severity')
            ev = mapping.get('evidence')
            assert sev == 'critical', f"expected severity 'critical', got {sev}"
            assert ev is not None, 'expected evidence JSON, got None'
    finally:
        # cleanup: ensure session is usable
        try:
            session.rollback()
        except Exception:
            pass
        session.query(Recommendation).filter(Recommendation.text == 'test rec').delete()
        session.query(Analysis).filter(Analysis.triggered_by == 'test').delete()
        session.commit()
        session.close()


def test_views_tolerate_missing_data():
    # self-contained: generate a small dataset so dates exist, then add a
    # service that has no activity/capacity and ensure views don't error.
    setup_test_data()
    session = SessionLocal()
    svc = Service(code='TMP', name='Tmp Service', description='tmp')
    session.add(svc)
    session.commit()
    sid = svc.id
    session.close()

    with engine.begin() as conn:
        with open('backend/db/bi_views/vw_service_summary.sql') as f:
            conn.execute(text(f.read()))
        # pick any date present in activity_records (always populated after setup)
        d = conn.execute(text('SELECT DISTINCT period_start::date FROM activity_records LIMIT 1')).scalar()
        assert d is not None, 'expected some activity date after setup'
        # ensure the row exists (should, because CROSS JOIN services x dates)
        row = conn.execute(text('SELECT service_id, admissions, expenses FROM vw_service_summary WHERE date = :d AND service_id = :sid'), {'d': d, 'sid': sid}).fetchone()
        assert row is not None, 'expected row for service with missing data'
        mapping = row._mapping
        # values should be zeros or NULL, not error
        assert mapping.get('admissions') is not None

    # cleanup
    session = SessionLocal()
    session.query(Service).filter(Service.id == sid).delete()
    session.commit()
    session.close()
