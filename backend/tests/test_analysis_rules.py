import pytest

from backend.app.analysis import rules


def test_rule_saturation_basic_ok():
    ctx = {'capacity_total': 100, 'occupied_beds_total': 50}
    res = rules.rule_saturation(ctx)
    assert res['rule_id'] == 'saturation_v1'
    assert res['status'] == 'ok'


def test_rule_saturation_triggered_global():
    ctx = {'capacity_total': 100, 'occupied_beds_total': 96}
    res = rules.rule_saturation(ctx)
    assert res['status'] == 'triggered'
    assert res['severity'] in ('alert', 'critical')


def test_rule_budget_overrun_basic():
    ctx = {
        'budget_by_service': {'s1': 1000.0, 's2': 500.0},
        'expenses_by_service': {'s1': 1100.0, 's2': 400.0},
    }
    res = rules.rule_budget_overrun(ctx)
    assert res['rule_id'] == 'budget_overrun_v1'
    assert res['status'] == 'triggered'
    assert 'details' in res['values']


def test_rule_energy_anomaly_not_evaluable():
    ctx = {'energy_total': None, 'admissions_total': None}
    res = rules.rule_energy_anomaly(ctx)
    assert res['status'] == 'not_evaluable'


def test_rule_staff_shortage_basic():
    ctx = {
        'staff_by_service': {'s1': {'nurse': 2}},
        'admissions_by_service': {'s1': 20},
        'period_days': 1,
    }
    res = rules.rule_staff_shortage(ctx)
    assert res['rule_id'] == 'staff_shortage_v1'
    assert 'details' in res['values']


def test_rule_saturation_capacity_zero():
    ctx = {'capacity_total': 0, 'occupied_beds_total': 0}
    res = rules.rule_saturation(ctx)
    assert res['status'] == 'not_evaluable'


def test_rule_budget_zero_triggered():
    ctx = {
        'budget_by_service': {'s1': 0.0},
        'expenses_by_service': {'s1': 100.0},
    }
    res = rules.rule_budget_overrun(ctx)
    assert res['status'] == 'triggered'
    assert res['values']['details']['s1']['severity'] == 'critical'


def test_rule_energy_anomaly_triggered():
    ctx = {
        'energy_per_admission_current': 3.2,
        'baseline_energy_per_admission': 1.0,
        'baseline_days': 30,
    }
    res = rules.rule_energy_anomaly(ctx)
    assert res['status'] == 'triggered'
    assert res['severity'] == 'critical'


def test_rule_staff_no_nurses():
    ctx = {
        'staff_by_service': {'s1': {'nurse': 0}},
        'admissions_by_service': {'s1': 5},
        'period_days': 1,
    }
    res = rules.rule_staff_shortage(ctx)
    assert res['status'] == 'triggered'
    assert res['values']['details']['s1']['severity'] == 'critical'


def test_rule_staff_accepts_flat_totals():
    # staff_roles_by_service returns nested role dicts, but flat headcount
    # totals (older providers) must not crash and should still evaluate.
    ctx = {
        'staff_by_service': {'s1': 2, 's2': 0},
        'admissions_by_service': {'s1': 5, 's2': 5},
        'period_days': 1,
    }
    res = rules.rule_staff_shortage(ctx)
    assert res['rule_id'] == 'staff_shortage_v1'
    assert 'details' in res['values']
    # s2 has 0 staff and admissions>0 -> must be flagged
    assert res['values']['details']['s2']['severity'] == 'critical'
