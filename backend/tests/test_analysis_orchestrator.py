from datetime import date

from backend.app.analysis import orchestrator


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


def provider_saturation():
    p = provider_normal()
    p.update({'occupied_beds_total': 190, 'capacity_total': 200, 'occupied_by_service': {1: 48, 2: 142}})
    return p


def provider_budget_overrun():
    p = provider_normal()
    p.update({'budget_by_service': {1: 100.0, 2: 200.0}, 'expenses_by_service': {1: 300.0, 2: 50.0}})
    return p


def provider_missing_budget():
    p = provider_normal()
    p.pop('budget_by_service', None)
    return p


def test_analysis_normal():
    r = orchestrator.run_analysis(start=date(2026, 8, 1), end=date(2026, 8, 1), kpi_provider=provider_normal())
    assert r['risk_level'] == 'ok'
    assert isinstance(r['kpi_snapshot'], dict)
    assert isinstance(r['rule_results'], list)


def test_analysis_saturation_triggers():
    r = orchestrator.run_analysis(start=date(2026, 8, 1), end=date(2026, 8, 1), kpi_provider=provider_saturation())
    # expect saturation triggered
    sat = next((x for x in r['rule_results'] if x['rule_id'] == 'saturation_v1'), None)
    assert sat is not None and sat['status'] == 'triggered'
    assert r['risk_level'] in ('critical', 'alert', 'warning')


def test_analysis_budget_overrun_triggers():
    r = orchestrator.run_analysis(start=date(2026, 8, 1), end=date(2026, 8, 1), kpi_provider=provider_budget_overrun())
    bud = next((x for x in r['rule_results'] if x['rule_id'] == 'budget_overrun_v1'), None)
    assert bud is not None and bud['status'] == 'triggered'
    assert any(r['severity'] for r in r['rule_results'] if r['status'] == 'triggered')


def test_analysis_rule_not_evaluable():
    r = orchestrator.run_analysis(start=date(2026, 8, 1), end=date(2026, 8, 1), kpi_provider=provider_missing_budget())
    bud = next((x for x in r['rule_results'] if x['rule_id'] == 'budget_overrun_v1'), None)
    assert bud is not None and bud['status'] == 'not_evaluable'


def test_overall_risk_calculation():
    # combine a critical and warning to ensure critical wins
    p = provider_normal()
    p['occupied_beds_total'] = 195
    p['capacity_total'] = 200
    p['budget_by_service'] = {1: 100.0}
    p['expenses_by_service'] = {1: 1000.0}
    r = orchestrator.run_analysis(start=date(2026, 8, 1), end=date(2026, 8, 1), kpi_provider=p)
    assert r['risk_level'] == 'critical'


def test_recommendations_generated():
    r = orchestrator.run_analysis(start=date(2026, 8, 1), end=date(2026, 8, 1), kpi_provider=provider_saturation())
    assert isinstance(r['recommendations'], list)
    assert len(r['recommendations']) >= 1
