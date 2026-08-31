from datetime import date

from backend.app.analysis import orchestrator
from backend.app.db.session import SessionLocal
from backend.app.models.models import Analysis, Recommendation


def provider_saturation():
    return {
        'admissions_total': 10,
        'discharges_total': 5,
        'occupied_beds_total': 190,
        'capacity_total': 200,
        'occupancy_rate': 0.95,
        'expenses_total': 1000.0,
        'energy_total': 500.0,
        'capacity_by_service': {1: 50, 2: 150},
        'occupied_by_service': {1: 48, 2: 142},
        'budget_by_service': {1: 10000.0, 2: 20000.0},
        'expenses_by_service': {1: 100.0, 2: 200.0},
        'staff_by_service': {1: 5, 2: 10},
        'admissions_by_service': {1: 2, 2: 8},
    }


def provider_normal():
    return {
        'admissions_total': 10,
        'discharges_total': 5,
        'occupied_beds_total': 20,
        'capacity_total': 200,
        'occupancy_rate': 0.10,
        'expenses_total': 1000.0,
        'energy_total': 500.0,
        'capacity_by_service': {1: 50, 2: 150},
        'occupied_by_service': {1: 5, 2: 15},
        'budget_by_service': {1: 10000.0, 2: 20000.0},
        'expenses_by_service': {1: 100.0, 2: 200.0},
        'staff_by_service': {1: 5, 2: 10},
        'admissions_by_service': {1: 2, 2: 8},
    }


def test_persist_analysis_with_recommendations():
    session = SessionLocal()
    prov = provider_saturation()
    r = orchestrator.run_analysis(start=date(2026, 8, 1), end=date(2026, 8, 1), kpi_provider=prov, persist=True, db_session=session)
    assert 'analysis_id' in r
    aid = r['analysis_id']
    a = session.query(Analysis).get(aid)
    assert a is not None
    recs = session.query(Recommendation).filter_by(analysis_id=aid).all()
    assert len(recs) == len(r['recommendations'])
    # cleanup
    for rec in recs:
        session.delete(rec)
    session.delete(a)
    session.commit()


def test_persist_analysis_without_recommendations():
    session = SessionLocal()
    prov = provider_normal()
    r = orchestrator.run_analysis(start=date(2026, 8, 2), end=date(2026, 8, 2), kpi_provider=prov, persist=True, db_session=session)
    aid = r['analysis_id']
    a = session.query(Analysis).get(aid)
    assert a is not None
    recs = session.query(Recommendation).filter_by(analysis_id=aid).all()
    assert len(recs) == 0
    session.delete(a)
    session.commit()


def test_transactional_rollback_on_recommendation_failure(monkeypatch):
    session = SessionLocal()

    class FaultyRecommendation:
        def __init__(self, *args, **kwargs):
            raise RuntimeError('simulate insert failure')

    # patch Recommendation in models so orchestrator uses faulty constructor
    monkeypatch.setattr('backend.app.models.models.Recommendation', FaultyRecommendation)

    prov = provider_saturation()
    triggered_by = 'test-rollback'
    try:
        orchestrator.run_analysis(start=date(2026, 8, 3), end=date(2026, 8, 3), kpi_provider=prov, persist=True, db_session=session, triggered_by=triggered_by)
        assert False, 'Expected exception from faulty Recommendation'
    except RuntimeError:
        # ensure no Analysis row persisted with triggered_by
        rows = session.query(Analysis).filter_by(triggered_by=triggered_by).all()
        assert len(rows) == 0
