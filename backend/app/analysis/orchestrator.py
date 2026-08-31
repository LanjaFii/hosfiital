"""Orchestrateur d'analyse Phase 4.

Fournit `run_analysis(...)` qui assemble un kpi_snapshot, exécute les règles
définies dans `rules.py` et retourne un rapport structuré. Peut être testé
en injectant un `kpi_provider` dict (pour éviter d'appeler la base).
"""
from typing import Optional, Dict, Any, List
from datetime import date, datetime

from backend.app.analysis import rules
from backend.app.etl import kpis as kpis_module


SEVERITY_ORDER = {'critical': 3, 'alert': 2, 'warning': 1, None: 0}


def _severity_rank(s: Optional[str]) -> int:
    return SEVERITY_ORDER.get(s, 0)


def _compute_overall_risk(rule_results: List[Dict[str, Any]]) -> str:
    max_rank = 0
    pick = None
    for r in rule_results:
        sev = r.get('severity')
        rank = _severity_rank(sev)
        if rank > max_rank:
            max_rank = rank
            pick = sev
    return pick or 'ok'


def _make_recommendations(rule_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    recs = []
    for r in rule_results:
        if r['status'] != 'triggered':
            continue
        text = f"Rule {r['rule_id']} triggered (severity={r['severity']}): {r['explanation']}"
        recs.append({'rule_id': r['rule_id'], 'severity': r['severity'], 'text': text})
    return recs


def _fetch_kpis_from_provider(provider: Optional[Dict[str, Any]], start: Optional[date], end: Optional[date], services: Optional[List[int]]):
    """Retourne un dict de KPIs soit depuis `provider` (dict), soit en appelant les fonctions kpis_module."""
    if provider is not None:
        return provider

    # Default: call kpis functions to build snapshot
    out: Dict[str, Any] = {}
    out['admissions_total'] = kpis_module.admissions_total(start, end)
    out['discharges_total'] = kpis_module.discharges_total(start, end)
    out['occupied_beds_total'] = kpis_module.occupied_beds_total(start, end)
    out['capacity_total'] = kpis_module.capacity_total(as_of=end)
    out['occupancy_rate'] = kpis_module.occupancy_rate_global(as_of=end, start=start, end=end)
    out['expenses_total'] = kpis_module.expenses_total(start, end)
    out['energy_total'] = kpis_module.energy_total(start, end)
    out['capacity_by_service'] = kpis_module.capacity_by_service(as_of=end)
    out['occupied_by_service'] = kpis_module.occupied_beds_by_service(start, end)
    out['budget_by_service'] = kpis_module.budget_by_service()
    out['expenses_by_service'] = kpis_module.expenses_by_service(start, end)
    out['staff_by_service'] = kpis_module.staff_by_service(as_of=end)
    out['admissions_by_service'] = {d['service_id']: d['admissions'] for d in kpis_module.admissions_by_service(start, end)}
    out['service_kpis'] = kpis_module.service_kpi_summary(start, end)
    return out


def run_analysis(start: Optional[date] = None, end: Optional[date] = None, services: Optional[List[int]] = None, kpi_provider: Optional[Dict[str, Any]] = None, triggered_by: Optional[str] = None, persist: bool = False, db_session=None) -> Dict[str, Any]:
    """Exécute une analyse et retourne le rapport.

    - `kpi_provider`: dict de KPIs (utilisé en tests) ou None pour appeler la DB.
    - `persist`: si True, persiste un `Analysis` + `Recommendation` (requiert `db_session`).
    """
    # snapshot
    kpis = _fetch_kpis_from_provider(kpi_provider, start, end, services)

    # Build contexts for rules
    rule_ctx_global = {
        'capacity_total': kpis.get('capacity_total'),
        'occupied_beds_total': kpis.get('occupied_beds_total'),
        'capacity_by_service': kpis.get('capacity_by_service'),
        'occupied_by_service': kpis.get('occupied_by_service'),
    }

    rule_ctx_budget = {
        'budget_by_service': kpis.get('budget_by_service'),
        'expenses_by_service': kpis.get('expenses_by_service'),
    }

    rule_ctx_energy = {
        'energy_per_admission_current': (kpis.get('energy_total') / kpis.get('admissions_total')) if kpis.get('admissions_total') else None,
        'energy_total': kpis.get('energy_total'),
        'admissions_total': kpis.get('admissions_total'),
        'baseline_energy_per_admission': kpis.get('baseline_energy_per_admission'),
        'baseline_days': kpis.get('baseline_days'),
    }

    rule_ctx_staff = {
        'staff_by_service': kpis.get('staff_by_service'),
        'admissions_by_service': kpis.get('admissions_by_service'),
        'period_days': ((end - start).days + 1) if start and end else 1,
    }

    # run rules
    results = []
    results.append(rules.rule_saturation(rule_ctx_global))
    results.append(rules.rule_budget_overrun(rule_ctx_budget))
    results.append(rules.rule_energy_anomaly(rule_ctx_energy))
    results.append(rules.rule_staff_shortage(rule_ctx_staff))

    overall_risk = _compute_overall_risk(results)
    recommendations = _make_recommendations(results)

    report = {
        'triggered_by': triggered_by,
        'triggered_at': datetime.utcnow().isoformat() + 'Z',
        'period': {'start': start.isoformat() if start else None, 'end': end.isoformat() if end else None},
        'kpi_snapshot': kpis,
        'rule_results': results,
        'risk_level': overall_risk,
        'recommendations': recommendations,
    }

    # optionally persist using models if requested
    if persist:
        if db_session is None:
            raise RuntimeError('db_session required when persist=True')
        # lazy import to avoid circular deps at module import time
        from backend.app.models.models import Analysis, Recommendation
        # Use an explicit transaction scope so failure rolls back everything
        with db_session.begin():
            a = Analysis(triggered_by=triggered_by, triggered_at=datetime.utcnow(), kpi_snapshot=report['kpi_snapshot'], anomalies=[r for r in results if r['status'] == 'triggered'], risk_level=overall_risk)
            db_session.add(a)
            db_session.flush()
            for rec in recommendations:
                r = Recommendation(analysis_id=a.id, service_id=None, text=rec['text'], type=rec['rule_id'], status='open')
                db_session.add(r)
        report['analysis_id'] = a.id

    return report
