from backend.app.db.session import engine
from sqlalchemy import inspect


def test_tables_exist():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    expected = [
        'services', 'beds', 'service_capacity', 'admissions', 'occupancy_snapshots',
        'activity_records', 'staff_levels', 'budgets', 'expenses', 'energy_consumption',
        'analyses', 'recommendations'
    ]
    for t in expected:
        assert t in tables, f"Table {t} should exist in the database"
