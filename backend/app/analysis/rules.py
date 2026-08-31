"""Règles métier v1 pour Phase 4.

Chaque règle est une fonction pure qui prend un contexte (dict) et retourne
un dict structuré:
  {
    'rule_id': str,
    'status': 'ok'|'triggered'|'not_evaluable',
    'severity': None|'warning'|'alert'|'critical',
    'explanation': str,
    'values': dict
  }

Les seuils V1 sont définis dans CONFIG et peuvent être externalisés plus tard.
"""
from typing import Dict, Any

# Configuration des seuils V1 (peuvent être externalisés plus tard)
CONFIG = {
    'saturation': {
        'global': {'warning': 0.90, 'alert': 0.95, 'critical': 0.98},
        'service': {'warning': 0.95, 'alert': 0.98, 'critical': 1.00},
        'trend_delta_pp': 5.0,  # percentage points
    },
    'budget': {
        'warning_pct': 0.05,  # 5%
        'alert_pct': 0.10,    # 10%
        'critical_pct': 1.0,  # >100% (optional)
    },
    'energy': {
        'mult_warning': 1.5,
        'mult_alert': 2.0,
        'mult_critical': 3.0,
        'baseline_days': 30,
    },
    'staff': {
        # admissions per staff per day thresholds (example for nurses)
        'nurse': {'warning': 3.0, 'alert': 5.0, 'critical': 7.0},
        'default': {'warning': 4.0, 'alert': 6.0, 'critical': 8.0},
    }
}


def _make_result(rule_id: str, status: str, severity: Any, explanation: str, values: Dict[str, Any]):
    return {
        'rule_id': rule_id,
        'status': status,
        'severity': severity,
        'explanation': explanation,
        'values': values,
    }


def rule_saturation(context: Dict[str, Any], cfg: Dict = CONFIG) -> Dict:
    """Detecte saturation globale ou par service.

    Contexte attendu (au moins les champs nécessaires) :
      - capacity_total (int)
      - occupied_beds_total (int)
      - capacity_by_service (dict service_id -> int) optional
      - occupied_by_service (dict service_id -> int) optional
      - trend: dict with 'recent_avg' and 'previous_avg' in percentage (optional)
    """
    rule_id = 'saturation_v1'
    try:
        cap = context.get('capacity_total')
        occ = context.get('occupied_beds_total')
        if cap is None or occ is None:
            return _make_result(rule_id, 'not_evaluable', None, 'Missing global capacity/occupancy data', {'capacity_total': cap, 'occupied_beds_total': occ})
        if cap == 0:
            return _make_result(rule_id, 'not_evaluable', None, 'Capacity is zero, cannot evaluate occupancy rate', {'capacity_total': cap})
        occ_rate = float(occ) / float(cap)
        # global thresholds
        gcfg = cfg['saturation']['global']
        sev = None
        status = 'ok'
        if occ_rate >= gcfg['critical']:
            sev = 'critical'
            status = 'triggered'
        elif occ_rate >= gcfg['alert']:
            sev = 'alert'
            status = 'triggered'
        elif occ_rate >= gcfg['warning']:
            sev = 'warning'
            status = 'triggered'

        explanation = f'Global occupancy rate = {occ_rate:.3f}'
        values = {'capacity_total': cap, 'occupied_beds_total': occ, 'occupancy_rate': occ_rate}

        # check per-service if provided
        svc_msgs = []
        caps = context.get('capacity_by_service') or {}
        occs = context.get('occupied_by_service') or {}
        scfg = cfg['saturation']['service']
        for sid, s_cap in list(caps.items()):
            s_occ = occs.get(sid, 0)
            if s_cap is None or s_cap == 0:
                continue
            s_rate = float(s_occ) / float(s_cap)
            if s_rate >= scfg['critical']:
                svc_msgs.append((sid, 'critical', s_rate))
            elif s_rate >= scfg['alert']:
                svc_msgs.append((sid, 'alert', s_rate))
            elif s_rate >= scfg['warning']:
                svc_msgs.append((sid, 'warning', s_rate))

        # If any service-level messages exist, record the worst one so recommendations
        # can reference a specific service. Do this even if global severity is already
        # triggered so callers can point to a service for mitigation.
        if svc_msgs:
            # escalate severity to highest service severity if needed
            levels = {'warning': 1, 'alert': 2, 'critical': 3}
            max_level = 0
            chosen = None
            for sid, ssev, srate in svc_msgs:
                lvl = levels[ssev]
                if lvl > max_level:
                    max_level = lvl
                    chosen = (ssev, sid, srate)
            if chosen:
                sev = chosen[0]
                status = 'triggered'
                explanation += f'; Service {chosen[1]} occupancy_rate={chosen[2]:.3f}'
                values['service_issue'] = {'service_id': chosen[1], 'occupancy_rate': chosen[2]}

        return _make_result(rule_id, status, sev, explanation, values)
    except Exception as e:
        return _make_result(rule_id, 'not_evaluable', None, f'Error evaluating saturation: {e}', {})


def rule_budget_overrun(context: Dict[str, Any], cfg: Dict = CONFIG) -> Dict:
    """Detecte dépassement budgétaire par service.

    Contexte attendu :
      - budget (number) OR budget_by_service dict
      - expenses (number) OR expenses_by_service dict
      - period_days (int, optional) for prorata
    """
    rule_id = 'budget_overrun_v1'
    try:
        # prefer per-service if provided
        budgets = context.get('budget_by_service')
        expenses = context.get('expenses_by_service')
        if budgets is None or expenses is None:
            return _make_result(rule_id, 'not_evaluable', None, 'Missing budget or expenses data', {'budget_by_service': budgets, 'expenses_by_service': expenses})

        results = {}
        for sid, bud in budgets.items():
            exp = float(expenses.get(sid, 0.0))
            if bud is None:
                results[sid] = {'status': 'not_evaluable', 'reason': 'budget missing'}
                continue
            if float(bud) == 0:
                # budget zero, if expenses > 0 then critical
                if exp > 0:
                    results[sid] = {'status': 'triggered', 'severity': 'critical', 'variance': -1.0}
                else:
                    results[sid] = {'status': 'ok', 'variance': 0.0}
                continue
            variance = float(bud) - exp
            rel = variance / float(bud)
            sev = None
            status = 'ok'
            bcfg = cfg['budget']
            if rel <= -bcfg['critical_pct']:
                sev = 'critical'
                status = 'triggered'
            elif rel <= -bcfg['alert_pct']:
                sev = 'alert'
                status = 'triggered'
            elif rel <= -bcfg['warning_pct']:
                sev = 'warning'
                status = 'triggered'
            results[sid] = {'status': status, 'severity': sev, 'variance': variance, 'relative': rel}

        # overall: triggered if any service triggered
        triggered_any = any(v.get('status') == 'triggered' for v in results.values())
        overall_sev = None
        if triggered_any:
            # pick worst severity
            order = {'warning': 1, 'alert': 2, 'critical': 3}
            maxlvl = 0
            for v in results.values():
                s = v.get('severity')
                if s and order.get(s, 0) > maxlvl:
                    maxlvl = order[s]
                    overall_sev = s
        return _make_result(rule_id, 'triggered' if triggered_any else 'ok', overall_sev, 'Budget variance evaluated', {'details': results})
    except Exception as e:
        return _make_result(rule_id, 'not_evaluable', None, f'Error evaluating budget: {e}', {})


def rule_energy_anomaly(context: Dict[str, Any], cfg: Dict = CONFIG) -> Dict:
    """Detecte anomalies de consommation énergétique.

    Contexte attendu :
      - energy_per_admission_current (float) OR energy_total & admissions_total
      - baseline_energy_per_admission (float) OR baseline_days available info
      - baseline_count_days (int) optional
    """
    rule_id = 'energy_anomaly_v1'
    try:
        current = context.get('energy_per_admission_current')
        baseline = context.get('baseline_energy_per_admission')
        baseline_days = context.get('baseline_days')
        if current is None:
            # try compute from totals
            et = context.get('energy_total')
            adm = context.get('admissions_total')
            if et is None or adm is None:
                return _make_result(rule_id, 'not_evaluable', None, 'Insufficient current energy/admissions data', {'energy_total': et, 'admissions_total': adm})
            if adm == 0:
                return _make_result(rule_id, 'not_evaluable', None, 'Zero admissions in current period', {'admissions_total': adm})
            current = float(et) / float(adm)

        if baseline is None or baseline_days is None or baseline_days < cfg['energy']['baseline_days']:
            return _make_result(rule_id, 'not_evaluable', None, 'Insufficient baseline history for evaluation', {'baseline': baseline, 'baseline_days': baseline_days})

        mult = current / float(baseline)
        ecfg = cfg['energy']
        sev = None
        status = 'ok'
        if mult >= ecfg['mult_critical']:
            sev = 'critical'; status = 'triggered'
        elif mult >= ecfg['mult_alert']:
            sev = 'alert'; status = 'triggered'
        elif mult >= ecfg['mult_warning']:
            sev = 'warning'; status = 'triggered'

        return _make_result(rule_id, status, sev, f'Energy per admission multiplier = {mult:.2f}', {'current': current, 'baseline': baseline, 'multiplier': mult, 'baseline_days': baseline_days})
    except Exception as e:
        return _make_result(rule_id, 'not_evaluable', None, f'Error evaluating energy: {e}', {})


def rule_staff_shortage(context: Dict[str, Any], cfg: Dict = CONFIG) -> Dict:
    """Detecte insuffisance des effectifs.

    Contexte attendu :
      - staff_by_service : dict service_id -> dict role -> headcount
      - admissions_by_service : dict service_id -> admissions_count (over period)
      - period_days (int) optional to normalize per day
    """
    rule_id = 'staff_shortage_v1'
    try:
        staff = context.get('staff_by_service')
        adm = context.get('admissions_by_service')
        period_days = context.get('period_days') or 1
        if staff is None or adm is None:
            return _make_result(rule_id, 'not_evaluable', None, 'Missing staff or admissions data', {'staff_by_service': staff, 'admissions_by_service': adm})

        details = {}
        triggered = False
        overall_sev = None
        order = {'warning': 1, 'alert': 2, 'critical': 3}
        for sid, roles in staff.items():
            total_recs = adm.get(sid, 0)
            if total_recs is None:
                continue
            # normalize per day
            per_day = float(total_recs) / float(period_days)
            # check per role, prefer nurse role thresholds
            nurse_count = roles.get('nurse') or 0
            thresholds = cfg['staff'].get('nurse') if 'nurse' in roles else cfg['staff']['default']
            # avoid division by zero
            if nurse_count == 0:
                if per_day > 0:
                    sev = 'critical'
                    details[sid] = {'status': 'triggered', 'severity': sev, 'reason': 'no nurses and admissions>0', 'per_day': per_day, 'nurse_count': nurse_count}
                    triggered = True
                    if order[sev] > order.get(overall_sev or 'warning'):
                        overall_sev = sev
                else:
                    details[sid] = {'status': 'ok', 'per_day': per_day, 'nurse_count': nurse_count}
                continue

            activity_per_nurse = per_day / float(nurse_count)
            sev = None
            status = 'ok'
            if activity_per_nurse >= thresholds['critical']:
                sev = 'critical'; status = 'triggered'
            elif activity_per_nurse >= thresholds['alert']:
                sev = 'alert'; status = 'triggered'
            elif activity_per_nurse >= thresholds['warning']:
                sev = 'warning'; status = 'triggered'

            details[sid] = {'status': status, 'severity': sev, 'activity_per_nurse': activity_per_nurse, 'nurse_count': nurse_count}
            if status == 'triggered':
                triggered = True
                if overall_sev is None or order[sev] > order.get(overall_sev):
                    overall_sev = sev

        return _make_result(rule_id, 'triggered' if triggered else 'ok', overall_sev, 'Staffing evaluated', {'details': details})
    except Exception as e:
        return _make_result(rule_id, 'not_evaluable', None, f'Error evaluating staff: {e}', {})
