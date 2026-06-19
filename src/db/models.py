from __future__ import annotations

from geoalchemy2 import Geometry
from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class CrimeRecord(Base):
    __tablename__ = "crime_records"
    __table_args__ = {"schema": "safestreet"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    occurrence_id = Column(String(50), unique=True, nullable=True)
    nature = Column(String(100), nullable=False)
    date = Column(DateTime, nullable=False)
    time = Column(String(5), nullable=False)
    geometry = Column(Geometry("POINT", srid=4326), nullable=False)
    h3_index = Column(String(20), nullable=True)


class InfrastructurePoint(Base):
    __tablename__ = "infrastructure_points"
    __table_args__ = {"schema": "safestreet"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    osm_id = Column(String(20), unique=True, nullable=True)
    infra_type = Column(String(50), nullable=False)
    geometry = Column(Geometry("POINT", srid=4326), nullable=False)
    h3_index = Column(String(20), nullable=True)


class H3Cell(Base):
    __tablename__ = "h3_cells"
    __table_args__ = {"schema": "safestreet"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    h3_index = Column(String(20), unique=True, nullable=False)
    resolution = Column(Integer, nullable=False)
    crime_count = Column(Integer, default=0)
    lighting_density = Column(Float, default=0.0)
    dist_nearest_lit = Column(Float, nullable=True)
    vulnerability_score = Column(Float, nullable=True)
    moran_cluster = Column(String(10), nullable=True)
