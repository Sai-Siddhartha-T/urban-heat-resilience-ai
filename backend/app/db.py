"""Metadata and results in SQLAlchemy; boundaries use PostGIS on PostgreSQL."""

import atexit
import os
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, String, JSON, DateTime, Text, Boolean, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from geoalchemy2 import Geometry
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT.parent / ".env")
(ROOT / "data").mkdir(exist_ok=True)
URL = os.getenv("DATABASE_URL") or f"sqlite:///{ROOT}/data/heatwise.db"
if URL.startswith("postgres://"):
    URL = URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    URL,
    connect_args={"check_same_thread": False, "timeout": 30} if URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)
POSTGIS = URL.startswith("postgresql")

# Legacy adapters still call save(). During route-owned ingestion their writes
# are deferred, so one city-scoped record and asset can be committed together.
_ACQUISITION_SCOPE = ContextVar("heatwise_acquisition_scope", default=False)
_ACQUISITION_KINDS = {"weather", "osm", "satellite", "monitoring", "groundwater"}


@contextmanager
def acquisition_scope():
    token = _ACQUISITION_SCOPE.set(True)
    try:
        yield
    finally:
        _ACQUISITION_SCOPE.reset(token)


def dispose_engine():
    engine.dispose()


atexit.register(dispose_engine)


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


class DataAsset(Base):
    """A normalized index of acquired evidence and its provenance."""

    __tablename__ = "data_assets"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    city: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    category: Mapped[str] = mapped_column(String, index=True)
    source: Mapped[str] = mapped_column(String, index=True)
    mode: Mapped[str] = mapped_column(String, index=True)
    analysis_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    provenance: Mapped[dict] = mapped_column(JSON)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class SchemaMigration(Base):
    __tablename__ = "schema_migrations"
    revision: Mapped[str] = mapped_column(String, primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def init_db():
    if POSTGIS:
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        except Exception as exc:
            import logging
            logging.getLogger("heatwise").warning(
                "PostGIS extension creation notice (extension may already exist or insufficient privileges): %s",
                exc,
            )
    from app.migrations import run_migrations

    run_migrations()


def save_asset(category, payload, provenance, asset_id=None):
    """Persist acquired evidence separately from analysis results."""
    from uuid import uuid4

    asset_id = asset_id or str(uuid4())
    with Session(engine) as session:
        row = session.get(DataAsset, asset_id)
        values = {
            "city": provenance.get("city"),
            "category": category,
            "source": provenance.get("source", category),
            "mode": provenance.get("mode", "live"),
            "analysis_ready": bool(provenance.get("analysis_ready")),
            "provenance": provenance,
            "payload": payload,
        }
        if row:
            for key, value in values.items():
                setattr(row, key, value)
        else:
            session.add(DataAsset(id=asset_id, **values))
        session.commit()
    return asset_id


def _asset_dict(row):
    return {
        "id": row.id, "city": row.city, "category": row.category,
        "source": row.source, "mode": row.mode,
        "analysis_ready": row.analysis_ready, "provenance": row.provenance,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "payload": row.payload,
    }


def asset_by_id(asset_id, city=None, mode=None):
    with Session(engine) as session:
        row = session.get(DataAsset, asset_id)
        if row is None or (city is not None and row.city != city) or (mode is not None and row.mode != mode):
            return None
        return _asset_dict(row)


def assets(city=None, category=None, limit=100, mode=None):
    with Session(engine) as session:
        query = select(DataAsset).order_by(DataAsset.created_at.desc())
        if city:
            query = query.where(DataAsset.city == city)
        if category:
            query = query.where(DataAsset.category == category)
        if mode:
            query = query.where(DataAsset.mode == mode)
        return [
            _asset_dict(row)
            for row in session.scalars(query.limit(limit))
        ]


def asset_summaries(city=None, category=None, limit=100, mode=None):
    """Return asset metadata without loading stored payloads."""
    with Session(engine) as session:
        query = select(
            DataAsset.id,
            DataAsset.city,
            DataAsset.category,
            DataAsset.source,
            DataAsset.mode,
            DataAsset.analysis_ready,
            DataAsset.provenance,
            DataAsset.created_at,
        ).order_by(DataAsset.created_at.desc())
        if city:
            query = query.where(DataAsset.city == city)
        if category:
            query = query.where(DataAsset.category == category)
        if mode:
            query = query.where(DataAsset.mode == mode)
        return [
            {
                "id": row.id,
                "city": row.city,
                "category": row.category,
                "source": row.source,
                "mode": row.mode,
                "analysis_ready": row.analysis_ready,
                "provenance": row.provenance,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in session.execute(query.limit(limit))
        ]


def persist_acquisition(category, payload, provenance):
    """Commit a normalized asset and one compatible raw record atomically."""
    from uuid import uuid4
    from app.provenance import canonical_category
    from app.schemas.evidence import EvidenceProvenance

    category = canonical_category(category)
    metadata = EvidenceProvenance.model_validate(provenance).model_dump()
    metadata["category"] = category
    identifier = str(uuid4())
    result = {
        **payload, "city": metadata["city"], "asset_id": identifier,
        "provenance": metadata, "analysis_ready": metadata["analysis_ready"],
    }
    record_kind = {
        "weather": "weather", "air_quality": "monitoring",
        "infrastructure": "osm", "groundwater": "groundwater",
    }.get(category, "satellite")
    with Session(engine) as session:
        session.add(DataAsset(
            id=identifier, city=metadata["city"], category=category,
            source=metadata["source"], mode=metadata["mode"],
            analysis_ready=metadata["analysis_ready"], provenance=metadata, payload=result,
        ))
        session.add(Record(id=str(uuid4()), kind=record_kind, payload=result))
        session.commit()
    return result


def save(kind, payload, record_id=None):
    from uuid import uuid4

    record_id = record_id or str(uuid4())
    if _ACQUISITION_SCOPE.get() and kind in _ACQUISITION_KINDS:
        return record_id
    with Session(engine) as session:
        row = session.get(Record, record_id)
        if row:
            row.payload = payload
        else:
            session.add(Record(id=record_id, kind=kind, payload=payload))
        session.commit()
    return record_id


def records(kind, limit=100, city=None):
    with Session(engine) as session:
        query = select(Record).where(Record.kind == kind)
        if city is not None:
            query = query.where(Record.payload["city"].as_string() == city)
        return [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat()
                if r.created_at
                else datetime.now(timezone.utc).isoformat(),
                **r.payload,
            }
            for r in session.scalars(
                query.order_by(Record.created_at.desc())
                .limit(limit)
            )
        ]
