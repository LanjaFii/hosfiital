from datetime import datetime, date, timedelta
from backend.app.db.session import engine
from backend.app.etl import kpis
from sqlalchemy import text


def _today():
    return date(2026, 8, 31)


def test_activity_by_service_and_day():
    conn = engine.connect()
    trans = conn.begin()
    try:
        # services
        conn.execute(text("insert into services (id, code, name, created_at) values (2001, 'S1', 'Serv1', now()) ON CONFLICT (id) DO UPDATE SET code=EXCLUDED.code, name=EXCLUDED.name, created_at=EXCLUDED.created_at"))
        conn.execute(text("insert into services (id, code, name, created_at) values (2002, 'S2', 'Serv2', now()) ON CONFLICT (id) DO UPDATE SET code=EXCLUDED.code, name=EXCLUDED.name, created_at=EXCLUDED.created_at"))
        # admissions
        baseline = kpis.admissions_total(date(2026,8,31), date(2026,9,1))
        baseline_by_day = kpis.admissions_by_day(date(2026,8,31), date(2026,9,1))
        baseline_by_service_list = kpis.admissions_by_service(date(2026,8,31), date(2026,9,1))
        baseline_by_service = {x['service_id']: x['admissions'] for x in baseline_by_service_list}
        conn.execute(text("insert into admissions (service_id, admitted_at) values (2001, '2026-08-31'), (2001, '2026-08-31'), (2002, '2026-09-01')"))
        # mark discharges for service 2001
        conn.execute(text("update admissions set discharged_at = '2026-09-02' where service_id = 2001"))
        # commit so other connections see the data
        trans.commit()

        a_total = kpis.admissions_total(date(2026,8,31), date(2026,9,1))
        assert a_total == baseline + 3
        by_day = kpis.admissions_by_day(date(2026,8,31), date(2026,9,1))
        assert by_day[date(2026,8,31)] == baseline_by_day.get(date(2026,8,31), 0) + 2
        assert by_day[date(2026,9,1)] == baseline_by_day.get(date(2026,9,1), 0) + 1
        by_service = kpis.admissions_by_service(date(2026,8,31), date(2026,9,1))
        s1 = next((x for x in by_service if x['service_id']==2001), None)
        assert (s1['admissions'] if s1 else 0) == baseline_by_service.get(2001, 0) + 2
    finally:
        # cleanup inserted data
        try:
            conn.execute(text("delete from admissions where service_id in (2001,2002)"))
            conn.execute(text("delete from services where id in (2001,2002)"))
        finally:
            conn.close()


def test_capacity_and_occupancy_and_rates():
    conn = engine.connect()
    trans = conn.begin()
    try:
        conn.execute(text("insert into services (id, code, name, created_at) values (3001, 'C1', 'Cap1', now()) ON CONFLICT (id) DO UPDATE SET code=EXCLUDED.code, name=EXCLUDED.name, created_at=EXCLUDED.created_at"))
        conn.execute(text("insert into service_capacity (service_id, as_of, beds_total) values (3001, '2026-08-01', 10) ON CONFLICT (service_id, as_of) DO UPDATE SET beds_total = EXCLUDED.beds_total"))
        conn.execute(text("delete from occupancy_snapshots where service_id = 3001 and snapshot_at = '2026-08-31'"))
        conn.execute(text("insert into occupancy_snapshots (service_id, snapshot_at, occupied_beds, available_beds) values (3001, '2026-08-31', 6, 4)"))
        trans.commit()
        assert kpis.capacity_total() >= 10
        caps = kpis.capacity_by_service()
        assert caps.get(3001) == 10
        occ = kpis.occupied_beds_total(date(2026,8,31), date(2026,8,31))
        assert occ >= 6
        occ_by = kpis.occupied_beds_by_service(date(2026,8,31), date(2026,8,31))
        assert occ_by.get(3001) == 6
        rate = kpis.occupancy_rate_global(as_of=None, start=date(2026,8,31), end=date(2026,8,31))
        assert rate is not None
    finally:
        try:
            conn.execute(text("delete from occupancy_snapshots where service_id = 3001"))
            conn.execute(text("delete from service_capacity where service_id = 3001"))
            conn.execute(text("delete from services where id = 3001"))
        finally:
            conn.close()


def test_staff_and_activity_ratio():
    conn = engine.connect()
    trans = conn.begin()
    try:
        conn.execute(text("insert into services (id, code, name, created_at) values (4001, 'HR1', 'HR1', now()) ON CONFLICT (id) DO UPDATE SET code=EXCLUDED.code, name=EXCLUDED.name, created_at=EXCLUDED.created_at"))
        conn.execute(text("delete from staff_levels where service_id = 4001 and as_of = '2026-08-30' and role = 'nurse'"))
        conn.execute(text("insert into staff_levels (service_id, as_of, role, headcount) values (4001, '2026-08-30', 'nurse', 5)"))
        conn.execute(text("insert into admissions (service_id, admitted_at) values (4001, '2026-08-31'), (4001, '2026-08-31')"))
        trans.commit()
        staff_total = kpis.staff_totals(as_of=date(2026,8,31))
        assert staff_total >= 5
        staff_by = kpis.staff_by_service(as_of=date(2026,8,31))
        assert staff_by.get(4001) == 5
        ratio = kpis.activity_per_staff(date(2026,8,31), date(2026,8,31))
        assert ratio is not None
    finally:
        try:
            conn.execute(text("delete from admissions where service_id = 4001"))
            conn.execute(text("delete from staff_levels where service_id = 4001"))
            conn.execute(text("delete from services where id = 4001"))
        finally:
            conn.close()


def test_finance_and_energy():
    conn = engine.connect()
    trans = conn.begin()
    try:
        conn.execute(text("insert into services (id, code, name, created_at) values (5001, 'F1', 'Fin1', now()) ON CONFLICT (id) DO UPDATE SET code=EXCLUDED.code, name=EXCLUDED.name, created_at=EXCLUDED.created_at"))
        conn.execute(text("insert into budgets (service_id, year, budget_amount) values (5001, 2026, 10000) ON CONFLICT (service_id, year) DO UPDATE SET budget_amount = EXCLUDED.budget_amount"))
        conn.execute(text("delete from expenses where service_id = 5001 and period_start = '2026-08-31' and amount = 2500"))
        conn.execute(text("insert into expenses (service_id, period_start, amount) values (5001, '2026-08-31', 2500)"))
        conn.execute(text("delete from energy_consumption where service_id = 5001 and measured_at = '2026-08-31'"))
        conn.execute(text("insert into energy_consumption (service_id, measured_at, consumption_kwh) values (5001, '2026-08-31', 120.5)"))
        trans.commit()
        b = kpis.budget_by_service()
        assert b.get(5001) == 10000.0
        e_by = kpis.expenses_by_service(date(2026,8,31), date(2026,8,31))
        assert e_by.get(5001) == 2500.0
        eng = kpis.energy_by_service(date(2026,8,31), date(2026,8,31))
        assert eng.get(5001) == 120.5
        var = kpis.budget_variance_by_service(date(2026,8,31), date(2026,8,31))
        assert 5001 in var and var[5001]['variance'] == 7500.0
    finally:
        try:
            conn.execute(text("delete from energy_consumption where service_id = 5001"))
            conn.execute(text("delete from expenses where service_id = 5001"))
            conn.execute(text("delete from budgets where service_id = 5001"))
            conn.execute(text("delete from services where id = 5001"))
        finally:
            conn.close()


def test_service_kpi_summary_and_persistence():
    conn = engine.connect()
    trans = conn.begin()
    try:
        # prepare service and metrics
        conn.execute(text("insert into services (id, code, name, created_at) values (6001, 'Sx', 'ServiceX', now()) ON CONFLICT (id) DO UPDATE SET code=EXCLUDED.code, name=EXCLUDED.name, created_at=EXCLUDED.created_at"))
        conn.execute(text("insert into service_capacity (service_id, as_of, beds_total) values (6001, '2026-08-01', 20) ON CONFLICT (service_id, as_of) DO UPDATE SET beds_total = EXCLUDED.beds_total"))
        conn.execute(text("delete from occupancy_snapshots where service_id = 6001 and snapshot_at = '2026-08-31'"))
        conn.execute(text("insert into occupancy_snapshots (service_id, snapshot_at, occupied_beds) values (6001, '2026-08-31', 10)"))
        conn.execute(text("insert into admissions (service_id, admitted_at) values (6001, '2026-08-31')"))
        conn.execute(text("insert into budgets (service_id, year, budget_amount) values (6001, 2026, 50000)"))
        conn.execute(text("insert into expenses (service_id, period_start, amount) values (6001, '2026-08-31', 10000)"))
        trans.commit()
        summary = kpis.service_kpi_summary(date(2026,8,31), date(2026,8,31))
        s = next(x for x in summary if x['service_id']==6001)
        assert s['capacity'] == 20
        assert s['occupied_beds'] == 10
        assert s['admissions'] == 1
        # persist daily KPI via run_pipeline
        from backend.app.etl.run_pipeline import run_pipeline
        ks = run_pipeline(start=date(2026,8,31), end=date(2026,8,31), persist=True)
        assert any(k['date'] == date(2026,8,31) for k in ks)
    finally:
        try:
            conn.execute(text("delete from kpi_daily where day = '2026-08-31'"))
            conn.execute(text("delete from expenses where service_id = 6001"))
            conn.execute(text("delete from budgets where service_id = 6001"))
            conn.execute(text("delete from admissions where service_id = 6001"))
            conn.execute(text("delete from occupancy_snapshots where service_id = 6001"))
            conn.execute(text("delete from service_capacity where service_id = 6001"))
            conn.execute(text("delete from services where id = 6001"))
        finally:
            conn.close()
