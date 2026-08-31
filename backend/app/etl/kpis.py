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
