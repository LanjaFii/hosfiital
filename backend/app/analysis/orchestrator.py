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


def _service_names_from_kpis(kpis: Optional[Dict[str, Any]]) -> Dict:
    """Build a service_id -> service_name map from the KPI snapshot `service_kpis`."""
    names: Dict = {}
    for item in (kpis or {}).get('service_kpis') or []:
        if isinstance(item, dict) and item.get('service_id') is not None:
            names[item.get('service_id')] = item.get('service_name')
    return names


def _service_label(sid, names: Dict) -> str:
    """Human label for a service id: its name when known, otherwise fallback."""
    if sid is None:
        return None
    name = names.get(sid)
    return name if name else f"le service {sid}"


def _recommendation_text(rule_id: str, severity, values: Dict[str, Any], names: Dict, budgets: Dict, expenses: Dict) -> tuple:
    """Return a human-readable, actionable (text, service_id) for a triggered rule."""
    svc = None

    if rule_id == 'saturation_v1':
        issue = values.get('service_issue') or {}
        svc = issue.get('service_id')
        s_rate = issue.get('occupancy_rate')
        occ = values.get('occupancy_rate')
        name = _service_label(svc, names)
        if name and s_rate is not None:
            return (
                f"Saturation {severity} : {name} est à {s_rate*100:.0f}% de sa capacité. "
                "Envisagez d'augmenter le nombre de lits ou de réorienter des patients "
                "vers d'autres services.", svc)
        if occ is not None:
            return (
                f"Saturation {severity} : le taux d'occupation global de l'hôpital est de "
                f"{occ*100:.0f}%. Envisagez d'augmenter la capacité ou de mieux répartir la charge.", None)
        return ("Saturation détectée : la capacité est dépassée. Envisagez d'augmenter la capacité.", svc)

    if rule_id == 'budget_overrun_v1':
        details = values.get('details') or {}
        for sid, info in details.items():
            if info.get('status') != 'triggered':
                continue
            try:
                svc = int(sid)
            except Exception:
                svc = sid
            name = _service_label(svc, names)
            exp = float(expenses.get(svc, 0.0) or 0.0)
            bud = budgets.get(svc)
            if bud:
                pct = (exp / float(bud)) * 100
                return (
                    f"Dépassement {severity} du budget de {name} : {exp:,.0f} € dépensés "
                    f"pour {bud:,.0f} € prévus ({pct:.0f}%). Envisagez de réduire les dépenses "
                    "ou de réviser ce budget.", svc)
            return (
                f"Dépassement {severity} du budget de {name} : {exp:,.0f} € dépensés. "
                "Envisagez de réduire les dépenses.", svc)
        return None

    if rule_id == 'energy_anomaly_v1':
        mult = values.get('multiplier')
        if mult is not None:
            return (
                f"Consommation énergétique anormalement élevée ({mult:.0f}× la normale). "
                "Envisagez un audit énergétique et des mesures d'économie.", None)
        return ("Consommation énergétique anormalement élevée. Envisagez un audit énergétique.", None)

    if rule_id == 'staff_shortage_v1':
        details = values.get('details') or {}
        for sid, info in details.items():
            if info.get('status') != 'triggered':
                continue
            try:
                svc = int(sid)
            except Exception:
                svc = sid
            name = _service_label(svc, names)
            per_day = info.get('per_day')
            nurses = info.get('nurse_count')
            apn = info.get('activity_per_nurse')
            if nurses == 0 and per_day:
                return (
                    f"Effectif insuffisant à {name} : {per_day:.1f} admissions/jour pour 0 infirmier. "
                    "Envisagez de recruter du personnel soignant.", svc)
            if apn is not None and nurses:
                return (
                    f"Charge de travail élevée à {name} : {apn:.2f} admissions/jour par infirmier. "
                    "Envisagez de renforcer les effectifs.", svc)
            return (f"Effectif insuffisant à {name}. Envisagez de renforcer les effectifs.", svc)
        return None

    return None


def _make_recommendations(rule_results: List[Dict[str, Any]], kpis: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    names = _service_names_from_kpis(kpis)
    budgets = (kpis or {}).get('budget_by_service') or {}
    expenses = (kpis or {}).get('expenses_by_service') or {}

    recs = []
    for r in rule_results:
        if r['status'] != 'triggered':
            continue
        rid = r['rule_id']
        sev = r['severity']
        vals = r.get('values') or {}
        pair = _recommendation_text(rid, sev, vals, names, budgets, expenses)
        if pair:
            text, svc = pair
        else:
            text, svc = (
                f"Alerte {sev or 'détectée'} sur la règle {rid}. Consultez le détail des indicateurs.",
                None,
            )
        recs.append({'rule_id': rid, 'severity': sev, 'text': text, 'service_id': svc})
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
    recommendations = _make_recommendations(results, kpis)

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
                svc_id = rec.get('service_id')
                # verify service exists in DB before assigning FK; if not, drop the link
                if svc_id is not None:
                    from backend.app.models.models import Service
                    if db_session.query(Service).get(svc_id) is None:
                        svc_id = None
                r = Recommendation(analysis_id=a.id, service_id=svc_id, text=rec['text'], type=rec['rule_id'], status='open')
                db_session.add(r)
        report['analysis_id'] = a.id

    return report
