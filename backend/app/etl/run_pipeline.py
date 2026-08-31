from datetime import date
from backend.app.db.session import engine
from .kpis import calculate_daily_kpis
from sqlalchemy import text


def persist_kpis(kpis):
    insert_sql = '''
    insert into kpi_daily (day, admissions_total, discharges_total, occupied_beds_total, capacity_total, occupancy_rate, expenses_total, energy_total)
    values (:day, :admissions_total, :discharges_total, :occupied_beds_total, :capacity_total, :occupancy_rate, :expenses_total, :energy_total)
    on conflict (day) do update set
      admissions_total = excluded.admissions_total,
      discharges_total = excluded.discharges_total,
      occupied_beds_total = excluded.occupied_beds_total,
      capacity_total = excluded.capacity_total,
      occupancy_rate = excluded.occupancy_rate,
      expenses_total = excluded.expenses_total,
      energy_total = excluded.energy_total
    '''
    from sqlalchemy import text as _text
    with engine.begin() as conn:
        for k in kpis:
            conn.execute(_text(insert_sql), {
                'day': k['date'],
                'admissions_total': k['admissions_total'],
                'discharges_total': k['discharges_total'],
                'occupied_beds_total': k['occupied_beds_total'],
                'capacity_total': k['capacity_total'],
                'occupancy_rate': k['occupancy_rate'],
                'expenses_total': k['expenses_total'],
                'energy_total': k['energy_total'],
            })


def run_pipeline(start: date = None, end: date = None, persist: bool = False):
    kpis = calculate_daily_kpis(start=start, end=end)
    if persist:
        persist_kpis(kpis)
    return kpis
