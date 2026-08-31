from sqlalchemy import Date
from backend.app.models.models import KpiDaily


def test_kpi_day_column_is_date():
    # SQLAlchemy Column type should be Date to match DB DATE
    col_type = KpiDaily.__table__.c.day.type
    assert isinstance(col_type, Date)
