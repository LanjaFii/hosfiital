from datetime import date
from decimal import Decimal
from typing import List, Dict, Optional
from backend.app.db.session import engine
from sqlalchemy import text


def _to_map(rows, key='d'):
    return {r[0]: r[1] for r in rows}


def calculate_daily_kpis(start: Optional[date] = None, end: Optional[date] = None) -> List[Dict]:
    params = {}
    # admissions
    with engine.connect() as conn:
        adm_rows = conn.execute(text("select admitted_at::date as d, count(*) as cnt from admissions group by admitted_at::date order by d"), params).fetchall()
        dis_rows = conn.execute(text("select discharged_at::date as d, count(*) as cnt from admissions where discharged_at is not null group by discharged_at::date order by d"), params).fetchall()
        occ_rows = conn.execute(text("select snapshot_at::date as d, sum(occupied_beds) as s from occupancy_snapshots group by snapshot_at::date order by d"), params).fetchall()
        exp_rows = conn.execute(text("select period_start::date as d, sum(amount) as s from expenses group by period_start::date order by d"), params).fetchall()
        en_rows = conn.execute(text("select measured_at::date as d, sum(consumption_kwh) as s from energy_consumption group by measured_at::date order by d"), params).fetchall()
        # capacity: take latest per service then sum
        cap_rows = conn.execute(text("select sum(beds_total) from (select distinct on (service_id) service_id, beds_total from service_capacity order by service_id, as_of desc) t"), params).fetchall()

    adm_map = {r[0]: int(r[1]) for r in adm_rows}
    dis_map = {r[0]: int(r[1]) for r in dis_rows}
    occ_map = {r[0]: int(r[1]) for r in occ_rows}
    exp_map = {r[0]: float(r[1]) for r in exp_rows}
    en_map = {r[0]: float(r[1]) for r in en_rows}
    cap_total = int(cap_rows[0][0] or 0)

    days = set()
    days.update(adm_map.keys())
    days.update(dis_map.keys())
    days.update(occ_map.keys())
    days.update(exp_map.keys())
    days.update(en_map.keys())

    results = []
    for d in sorted(days):
        admissions_total = adm_map.get(d, 0)
        discharges_total = dis_map.get(d, 0)
        occupied_beds_total = occ_map.get(d, 0)
        capacity_total = cap_total
        occupancy_rate = None
        if capacity_total and capacity_total != 0:
            occupancy_rate = float((Decimal(occupied_beds_total) / Decimal(capacity_total)) * 100)
        results.append({
            'date': d,
            'admissions_total': admissions_total,
            'discharges_total': discharges_total,
            'occupied_beds_total': occupied_beds_total,
            'capacity_total': capacity_total,
            'occupancy_rate': occupancy_rate,
            'expenses_total': exp_map.get(d, 0.0),
            'energy_total': en_map.get(d, 0.0),
        })

    return results


def _date_params(start: Optional[date], end: Optional[date]):
    params = {}
    cond = []
    if start:
        params['start'] = start
    if end:
        params['end'] = end
    return params


def admissions_total(start: Optional[date] = None, end: Optional[date] = None) -> int:
    q = "select count(*) from admissions"
    params = _date_params(start, end)
    if start and end:
        q += " where admitted_at::date between :start and :end"
    elif start:
        q += " where admitted_at::date >= :start"
    elif end:
        q += " where admitted_at::date <= :end"
    with engine.connect() as conn:
        return int(conn.execute(text(q), params).scalar() or 0)


def discharges_total(start: Optional[date] = None, end: Optional[date] = None) -> int:
    q = "select count(*) from admissions where discharged_at is not null"
    params = _date_params(start, end)
    if start and end:
        q += " and discharged_at::date between :start and :end"
    elif start:
        q += " and discharged_at::date >= :start"
    elif end:
        q += " and discharged_at::date <= :end"
    with engine.connect() as conn:
        return int(conn.execute(text(q), params).scalar() or 0)


def admissions_by_day(start: Optional[date], end: Optional[date]):
    q = "select admitted_at::date as d, count(*) as cnt from admissions"
    params = _date_params(start, end)
    if start and end:
        q += " where admitted_at::date between :start and :end"
    q += " group by d order by d"
    with engine.connect() as conn:
        return {r[0]: int(r[1]) for r in conn.execute(text(q), params).fetchall()}


def discharges_by_day(start: Optional[date], end: Optional[date]):
    q = "select discharged_at::date as d, count(*) as cnt from admissions where discharged_at is not null"
    params = _date_params(start, end)
    if start and end:
        q += " and discharged_at::date between :start and :end"
    q += " group by d order by d"
    with engine.connect() as conn:
        return {r[0]: int(r[1]) for r in conn.execute(text(q), params).fetchall()}


def admissions_by_service(start: Optional[date], end: Optional[date]):
    q = "select s.id, s.name, count(a.id) from services s left join admissions a on a.service_id = s.id"
    params = _date_params(start, end)
    if start and end:
        q += " and a.admitted_at::date between :start and :end"
    q += " group by s.id, s.name order by s.name"
    with engine.connect() as conn:
        return [{ 'service_id': r[0], 'service_name': r[1], 'admissions': int(r[2]) } for r in conn.execute(text(q), params).fetchall()]


def discharges_by_service(start: Optional[date], end: Optional[date]):
    q = "select s.id, s.name, count(a.id) from services s left join admissions a on a.service_id = s.id and a.discharged_at is not null"
    params = _date_params(start, end)
    if start and end:
        q += " and a.discharged_at::date between :start and :end"
    q += " group by s.id, s.name order by s.name"
    with engine.connect() as conn:
        return [{ 'service_id': r[0], 'service_name': r[1], 'discharges': int(r[2]) } for r in conn.execute(text(q), params).fetchall()]


def capacity_total(as_of: Optional[date] = None) -> int:
    # sum latest beds_total per service as of given date (or latest overall)
    params = {}
    if as_of:
        params['as_of'] = as_of
        q = "select sum(beds_total) from (select distinct on (service_id) service_id, beds_total from service_capacity where as_of <= :as_of order by service_id, as_of desc) t"
    else:
        q = "select sum(beds_total) from (select distinct on (service_id) service_id, beds_total from service_capacity order by service_id, as_of desc) t"
    with engine.connect() as conn:
        return int(conn.execute(text(q), params).scalar() or 0)


def capacity_by_service(as_of: Optional[date] = None):
    params = {}
    if as_of:
        params['as_of'] = as_of
        q = "select service_id, beds_total from (select distinct on (service_id) service_id, beds_total from service_capacity where as_of <= :as_of order by service_id, as_of desc) t"
    else:
        q = "select service_id, beds_total from (select distinct on (service_id) service_id, beds_total from service_capacity order by service_id, as_of desc) t"
    with engine.connect() as conn:
        return {r[0]: int(r[1]) for r in conn.execute(text(q), params).fetchall()}


def occupied_beds_total(start: Optional[date] = None, end: Optional[date] = None) -> int:
    q = "select sum(occupied_beds) from occupancy_snapshots"
    params = _date_params(start, end)
    if start and end:
        q += " where snapshot_at::date between :start and :end"
    with engine.connect() as conn:
        return int(conn.execute(text(q), params).scalar() or 0)


def occupied_beds_by_service(start: Optional[date] = None, end: Optional[date] = None):
    q = "select service_id, sum(occupied_beds) from occupancy_snapshots"
    params = _date_params(start, end)
    if start and end:
        q += " where snapshot_at::date between :start and :end"
    q += " group by service_id"
    with engine.connect() as conn:
        return {r[0]: int(r[1]) for r in conn.execute(text(q), params).fetchall()}


def occupancy_rate_global(as_of: Optional[date] = None, start: Optional[date] = None, end: Optional[date] = None) -> Optional[float]:
    cap = capacity_total(as_of=as_of)
    occ = occupied_beds_total(start=start, end=end)
    if not cap or cap == 0:
        return None
    return float((Decimal(occ) / Decimal(cap)) * 100)


def occupancy_rate_by_service(as_of: Optional[date] = None, start: Optional[date] = None, end: Optional[date] = None):
    caps = capacity_by_service(as_of=as_of)
    occs = occupied_beds_by_service(start=start, end=end)
    out = {}
    for sid, cap in caps.items():
        occ = occs.get(sid, 0)
        rate = None
        if cap and cap != 0:
            rate = float((Decimal(occ) / Decimal(cap)) * 100)
        out[sid] = {'capacity': cap, 'occupied': occ, 'occupancy_rate': rate}
    return out


def staff_totals(as_of: Optional[date] = None):
    params = {}
    if as_of:
        params['as_of'] = as_of
        q = "select sum(headcount) from (select distinct on (service_id, role) service_id, role, headcount from staff_levels where as_of <= :as_of order by service_id, role, as_of desc) t"
    else:
        q = "select sum(headcount) from (select distinct on (service_id, role) service_id, role, headcount from staff_levels order by service_id, role, as_of desc) t"
    with engine.connect() as conn:
        return int(conn.execute(text(q), params).scalar() or 0)


def staff_by_service(as_of: Optional[date] = None):
    params = {}
    if as_of:
        params['as_of'] = as_of
        q = "select service_id, sum(headcount) from (select distinct on (service_id, role) service_id, role, headcount from staff_levels where as_of <= :as_of order by service_id, role, as_of desc) t group by service_id"
    else:
        q = "select service_id, sum(headcount) from (select distinct on (service_id, role) service_id, role, headcount from staff_levels order by service_id, role, as_of desc) t group by service_id"
    with engine.connect() as conn:
        return {r[0]: int(r[1]) for r in conn.execute(text(q), params).fetchall()}


def staff_by_role(as_of: Optional[date] = None):
    params = {}
    if as_of:
        params['as_of'] = as_of
        q = "select role, sum(headcount) from (select distinct on (service_id, role) service_id, role, headcount from staff_levels where as_of <= :as_of order by service_id, role, as_of desc) t group by role"
    else:
        q = "select role, sum(headcount) from (select distinct on (service_id, role) service_id, role, headcount from staff_levels order by service_id, role, as_of desc) t group by role"
    with engine.connect() as conn:
        return {r[0]: int(r[1]) for r in conn.execute(text(q), params).fetchall()}


def activity_per_staff(start: Optional[date] = None, end: Optional[date] = None):
    adm = admissions_total(start, end)
    staff = staff_totals(as_of=end)
    if not staff or staff == 0:
        return None
    return float(Decimal(adm) / Decimal(staff))


def budget_by_service():
    q = "select service_id, sum(budget_amount) from budgets group by service_id"
    with engine.connect() as conn:
        return {r[0]: float(r[1]) for r in conn.execute(text(q)).fetchall()}


def budget_total():
    q = "select sum(budget_amount) from budgets"
    with engine.connect() as conn:
        return float(conn.execute(text(q)).scalar() or 0.0)


def expenses_by_service(start: Optional[date] = None, end: Optional[date] = None):
    q = "select service_id, sum(amount) from expenses"
    params = _date_params(start, end)
    if start and end:
        q += " where period_start::date between :start and :end"
    q += " group by service_id"
    with engine.connect() as conn:
        return {r[0]: float(r[1]) for r in conn.execute(text(q), params).fetchall()}


def expenses_total(start: Optional[date] = None, end: Optional[date] = None):
    q = "select sum(amount) from expenses"
    params = _date_params(start, end)
    if start and end:
        q += " where period_start::date between :start and :end"
    with engine.connect() as conn:
        return float(conn.execute(text(q), params).scalar() or 0.0)


def budget_variance_by_service(start: Optional[date] = None, end: Optional[date] = None):
    b = budget_by_service()
    e = expenses_by_service(start, end)
    out = {}
    for sid, bud in b.items():
        exp = e.get(sid, 0.0)
        out[sid] = { 'budget': bud, 'expenses': exp, 'variance': float(bud - exp), 'consumption_rate': (float(exp / bud * 100) if bud and bud != 0 else None) }
    return out


def energy_total(start: Optional[date] = None, end: Optional[date] = None):
    q = "select sum(consumption_kwh) from energy_consumption"
    params = _date_params(start, end)
    if start and end:
        q += " where measured_at::date between :start and :end"
    with engine.connect() as conn:
        return float(conn.execute(text(q), params).scalar() or 0.0)


def energy_by_service(start: Optional[date] = None, end: Optional[date] = None):
    q = "select service_id, sum(consumption_kwh) from energy_consumption"
    params = _date_params(start, end)
    if start and end:
        q += " where measured_at::date between :start and :end"
    q += " group by service_id"
    with engine.connect() as conn:
        return {r[0]: float(r[1]) for r in conn.execute(text(q), params).fetchall()}


def service_kpi_summary(start: Optional[date] = None, end: Optional[date] = None):
    # returns per-service summary: occupancy_rate, admissions, expenses, energy
    adm = {d['service_id']: d['admissions'] for d in admissions_by_service(start, end)}
    dis = {d['service_id']: d['discharges'] for d in discharges_by_service(start, end)}
    caps = capacity_by_service(as_of=end)
    occs = occupied_beds_by_service(start, end)
    exps = expenses_by_service(start, end)
    ens = energy_by_service(start, end)
    # get service names
    with engine.connect() as conn:
        services = {r[0]: r[1] for r in conn.execute(text('select id, name from services')).fetchall()}

    out = []
    for sid, name in services.items():
        cap = caps.get(sid, 0)
        occ = occs.get(sid, 0)
        rate = None
        if cap and cap != 0:
            rate = float((Decimal(occ) / Decimal(cap)) * 100)
        out.append({
            'service_id': sid,
            'service_name': name,
            'occupancy_rate': rate,
            'occupied_beds': occ,
            'capacity': cap,
            'admissions': adm.get(sid, 0),
            'discharges': dis.get(sid, 0),
            'expenses': exps.get(sid, 0.0),
            'energy': ens.get(sid, 0.0),
        })
    return out
