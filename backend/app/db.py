"""Metadata and results in SQLAlchemy; boundaries use PostGIS on PostgreSQL."""

import os
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, String, JSON, DateTime, Text, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from geoalchemy2 import Geometry
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT.parent / ".env")
(ROOT / "data").mkdir(exist_ok=True)
URL = os.getenv("DATABASE_URL") or f"sqlite:///{ROOT}/data/heatwise.db"
engine = create_engine(
    URL,
    connect_args={"check_same_thread": False} if URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)
POSTGIS = URL.startswith("postgresql")


class Base(DeclarativeBase):
    pass


class Record(Base):
    __tablename__ = "analysis_records"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Zone(Base):
    __tablename__ = "zones"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    city: Mapped[str] = mapped_column(String, index=True)
    properties: Mapped[dict] = mapped_column(JSON)
    boundary = mapped_column(Geometry("POLYGON", srid=4326) if POSTGIS else Text)


def init_db():
    if POSTGIS:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.create_all(engine)


def save(kind, payload, record_id=None):
    from uuid import uuid4

    record_id = record_id or str(uuid4())
    with Session(engine) as session:
        row = session.get(Record, record_id)
        if row:
            row.payload = payload
        else:
            session.add(Record(id=record_id, kind=kind, payload=payload))
        session.commit()
    return record_id


def records(kind, limit=100):
    with Session(engine) as session:
        return [
            {"id": r.id, "created_at": r.created_at.isoformat(), **r.payload}
            for r in session.scalars(
                select(Record)
                .where(Record.kind == kind)
                .order_by(Record.created_at.desc())
                .limit(limit)
            )
        ]
