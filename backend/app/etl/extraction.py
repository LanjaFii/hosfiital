from typing import Optional
from backend.app.db.session import engine
from sqlalchemy import text


def fetch_table(table_name: str, start: Optional[str] = None, end: Optional[str] = None):
    sql = f"select * from {table_name}"
    if start or end:
        conds = []
        if start:
            conds.append(f"(coalesce(period_start::date, snapshot_at::date, measured_at::date) >= :start)")
        if end:
            conds.append(f"(coalesce(period_end::date, snapshot_at::date, measured_at::date) <= :end)")
        sql += " where " + " and ".join(conds)

    with engine.connect() as conn:
        return conn.execute(text(sql), {"start": start, "end": end}).fetchall()


def load_services():
    with engine.connect() as conn:
        return conn.execute(text("select * from services")).fetchall()


def load_occupancy_snapshots(start: Optional[str] = None, end: Optional[str] = None):
    return fetch_table("occupancy_snapshots", start, end)


def load_activity_records(start: Optional[str] = None, end: Optional[str] = None):
    return fetch_table("activity_records", start, end)


def load_service_capacity():
    with engine.connect() as conn:
        return conn.execute(text("select * from service_capacity")).fetchall()


def load_staff_levels():
    with engine.connect() as conn:
        return conn.execute(text("select * from staff_levels")).fetchall()


def load_budgets():
    with engine.connect() as conn:
        return conn.execute(text("select * from budgets")).fetchall()


def load_expenses(start: Optional[str] = None, end: Optional[str] = None):
    return fetch_table("expenses", start, end)


def load_energy(start: Optional[str] = None, end: Optional[str] = None):
    return fetch_table("energy_consumption", start, end)
