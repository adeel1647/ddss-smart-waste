from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, Float, DateTime, ForeignKey, Integer, Index, func
from typing import List, Optional

class Base(DeclarativeBase):
    pass

class Bin(Base):
    __tablename__ = "bins"

    bin_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    postcode: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    telemetry: Mapped[List["Telemetry"]] = relationship(back_populates="bin", cascade="all, delete-orphan")
    classifications: Mapped[List["Classification"]] = relationship(back_populates="bin", cascade="all, delete-orphan")

class Telemetry(Base):
    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bin_id: Mapped[str] = mapped_column(ForeignKey("bins.bin_id", ondelete="CASCADE"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    fill_level: Mapped[float] = mapped_column(Float, nullable=False)
    last_collection_hours: Mapped[float] = mapped_column(Float, nullable=False)

    bin: Mapped["Bin"] = relationship(back_populates="telemetry")

    __table_args__ = (Index("ix_telemetry_bin_ts", "bin_id", "ts"),)

class Classification(Base):
    __tablename__ = "classifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bin_id: Mapped[str] = mapped_column(ForeignKey("bins.bin_id", ondelete="CASCADE"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    predicted_class: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    bin: Mapped["Bin"] = relationship(back_populates="classifications")

    __table_args__ = (Index("ix_classifications_bin_ts", "bin_id", "ts"),)

class DecisionRun(Base):
    __tablename__ = "decision_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    postcode_filter: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    items: Mapped[List["DecisionItem"]] = relationship(back_populates="run", cascade="all, delete-orphan")

class DecisionItem(Base):
    __tablename__ = "decision_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("decision_runs.id", ondelete="CASCADE"), index=True)

    bin_id: Mapped[str] = mapped_column(String(64), index=True)
    predicted_class: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    uncertainty: Mapped[float] = mapped_column(Float, nullable=False)

    current_fill: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_fill_6h: Mapped[float] = mapped_column(Float, nullable=False)
    last_collection_hours: Mapped[float] = mapped_column(Float, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)

    alerts_json: Mapped[str] = mapped_column(String, nullable=False, default="[]")

    run: Mapped["DecisionRun"] = relationship(back_populates="items")

class RoutePlan(Base):
    __tablename__ = "route_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    decision_run_id: Mapped[int] = mapped_column(Integer, index=True)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    capacity: Mapped[float] = mapped_column(Float, nullable=False)

    depot_lat: Mapped[float] = mapped_column(Float, nullable=False)
    depot_lon: Mapped[float] = mapped_column(Float, nullable=False)

    total_distance_km: Mapped[float] = mapped_column(Float, nullable=False)

    trips: Mapped[List["RouteTrip"]] = relationship(back_populates="plan", cascade="all, delete-orphan")

class RouteTrip(Base):
    __tablename__ = "route_trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("route_plans.id", ondelete="CASCADE"), index=True)
    trip_index: Mapped[int] = mapped_column(Integer, nullable=False)
    stops_json: Mapped[str] = mapped_column(String, nullable=False)
    trip_distance_km: Mapped[float] = mapped_column(Float, nullable=False)

    plan: Mapped["RoutePlan"] = relationship(back_populates="trips")

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())