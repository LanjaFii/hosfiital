import os, sys
from datetime import datetime, timedelta

# ensure project root on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.generators.scenarios import run_scenario
from backend.app.analysis import rules as rules_module
from backend.app.etl import kpis as kpis_module
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.models.models import Analysis, Recommendation


client = TestClient(app)


def run_and_post_analysis(scenario_name, days=7, seed=42):
    start = datetime.utcnow().date()
    run_scenario(name=scenario_name, days=days, seed=seed, start_date=start, reset=True)
    # analyze last day
    day = start + timedelta(days=days - 1)
    payload = {'start': day.isoformat(), 'end': day.isoformat(), 'triggered_by': f'e2e-{scenario_name}'}
    r = client.post('/analyses', json=payload)
    assert r.status_code == 201
    return r.json()['analysis_id']


def fetch_analysis(aid):
    g = client.get(f'/analyses/{aid}')
    assert g.status_code == 200
    return g.json()


def cleanup_analysis(aid):
    session = SessionLocal()
    session.query(Recommendation).filter_by(analysis_id=aid).delete()
    session.query(Analysis).filter_by(id=aid).delete()
    session.commit()
    session.close()


def test_e2e_normal():
    aid = run_and_post_analysis('normal', days=5, seed=123)
    data = fetch_analysis(aid)
    # risk should not be critical
    assert data['risk_level'] != 'critical'
    cleanup_analysis(aid)


def test_e2e_saturation():
    aid = run_and_post_analysis('saturation', days=10, seed=7)
    data = fetch_analysis(aid)
    # expect at least one triggered anomaly related to saturation
    anomalies = data.get('anomalies') or []
    sat = [a for a in anomalies if a.get('rule_id') == 'saturation_v1']
    # expect at least one triggered anomaly related to saturation
    assert len(sat) >= 1
    # check recommendations include service_id or anomalies indicate service
    recs = data.get('recommendations') or []
    assert len(recs) >= 1
    # at least one recommendation or anomaly should reference a service or service_issue
    has_service = any(r.get('service_id') for r in recs) or any(a.get('values', {}).get('service_issue') for a in anomalies)
    assert has_service
    cleanup_analysis(aid)


def test_e2e_budget_overrun():
    aid = run_and_post_analysis('budget_overrun', days=10, seed=9)
    data = fetch_analysis(aid)
    anomalies = data.get('anomalies') or []
    bud = [a for a in anomalies if a.get('rule_id') == 'budget_overrun_v1']
    # expect at least one triggered anomaly related to budget overrun
    assert len(bud) >= 1
    recs = data.get('recommendations') or []
    assert len(recs) >= 1
    # ensure at least one recommendation relates to budget (text contains 'budget' or rule_id)
    assert any('budget' in r.get('text', '').lower() or r.get('rule_id') == 'budget_overrun_v1' for r in recs)
    cleanup_analysis(aid)
