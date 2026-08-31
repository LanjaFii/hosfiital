from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    Index,
    Numeric,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .base import Base


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    type = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    beds = relationship("Bed", back_populates="service")


class Bed(Base):
    __tablename__ = "beds"

    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    bed_code = Column(String(100), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    service = relationship("Service", back_populates="beds")


class ServiceCapacity(Base):
    __tablename__ = "service_capacity"

    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    as_of = Column(DateTime, nullable=False)
    beds_total = Column(Integer, nullable=False)
    notes = Column(Text)

    __table_args__ = (UniqueConstraint("service_id", "as_of", name="u_service_capacity_asof"),)


class Admission(Base):
    __tablename__ = "admissions"

    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    admitted_at = Column(DateTime, nullable=False)
    discharged_at = Column(DateTime, nullable=True)
    patient_hash = Column(String(128), nullable=True)
    age_group = Column(String(50), nullable=True)
    sex = Column(String(10), nullable=True)
    source = Column(String(100), nullable=True)
    reason = Column(String(200), nullable=True)
    bed_id = Column(Integer, ForeignKey("beds.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default="active")


class OccupancySnapshot(Base):
    __tablename__ = "occupancy_snapshots"

    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    snapshot_at = Column(DateTime, nullable=False)
    occupied_beds = Column(Integer, nullable=False)
    available_beds = Column(Integer, nullable=True)
    notes = Column(Text)

    __table_args__ = (Index("ix_occupancy_service_snapshot", "service_id", "snapshot_at"),)


class ActivityRecord(Base):
    __tablename__ = "activity_records"

    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    admissions_count = Column(Integer, default=0)
    discharges_count = Column(Integer, default=0)
    visits_count = Column(Integer, default=0)
    metric_payload = Column(JSONB)

    __table_args__ = (Index("ix_activity_service_period", "service_id", "period_start", "period_end"),)


class StaffLevel(Base):
    __tablename__ = "staff_levels"

    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    as_of = Column(DateTime, nullable=False)
    role = Column(String(50), nullable=False)
    headcount = Column(Integer, nullable=False)
    fte = Column(Numeric, nullable=True)
    notes = Column(Text)

    __table_args__ = (Index("ix_staff_service_asof_role", "service_id", "as_of", "role"),)


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    year = Column(Integer, nullable=False)
    budget_amount = Column(Numeric, nullable=False)
    currency = Column(String(10), default="EUR")

    __table_args__ = (UniqueConstraint("service_id", "year", name="u_budget_service_year"),)


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    amount = Column(Numeric, nullable=False)
    currency = Column(String(10), default="EUR")
    category = Column(String(100), nullable=True)
    description = Column(Text)
    recorded_at = Column(DateTime, default=datetime.utcnow)


class EnergyConsumption(Base):
    __tablename__ = "energy_consumption"

    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    measured_at = Column(DateTime, nullable=False)
    consumption_kwh = Column(Numeric, nullable=False)
    cost = Column(Numeric, nullable=True)
    source = Column(String(100), nullable=True)
    metadata_json = Column(JSONB)


class KpiDaily(Base):
    __tablename__ = "kpi_daily"

    day = Column(Date, primary_key=True)
    admissions_total = Column(Integer)
    discharges_total = Column(Integer)
    occupied_beds_total = Column(Integer)
    capacity_total = Column(Integer)
    occupancy_rate = Column(Numeric)
    expenses_total = Column(Numeric)
    energy_total = Column(Numeric)


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True)
    triggered_by = Column(String(200), nullable=True)
    triggered_at = Column(DateTime, nullable=False)
    kpi_snapshot = Column(JSONB)
    anomalies = Column(JSONB)
    risk_level = Column(String(20), nullable=True)
    notes = Column(Text)

    recommendations = relationship("Recommendation", back_populates="analysis", cascade="all, delete-orphan")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    text = Column(Text, nullable=False)
    type = Column(String(50), nullable=True)
    status = Column(String(20), default="open")
    created_at = Column(DateTime, default=datetime.utcnow)

    analysis = relationship("Analysis", back_populates="recommendations")
