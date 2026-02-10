# src/carms_platform/models.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlmodel import SQLModel, Field


class Discipline(SQLModel, table=True):
    __tablename__ = "discipline"

    discipline_id: int = Field(primary_key=True)
    discipline: str


class ProgramStream(SQLModel, table=True):
    __tablename__ = "program_stream"

    # One row per program stream (for a given match cycle)
    program_stream_id: int = Field(primary_key=True)

    match_cycle_id: int = Field(index=True)  # e.g., 1503

    discipline_id: Optional[int] = Field(default=None, foreign_key="discipline.discipline_id", index=True)
    discipline_name: Optional[str] = Field(default=None)

    school_id: Optional[int] = Field(default=None, index=True)
    school_name: Optional[str] = Field(default=None)

    program_stream_name: Optional[str] = Field(default=None)
    program_site: Optional[str] = Field(default=None)
    program_stream: Optional[str] = Field(default=None)

    program_name: Optional[str] = Field(default=None)
    program_url: Optional[str] = Field(default=None)

    row_index: Optional[int] = Field(default=None)  # holds Excel "Unnamed: 0" if present


class ProgramDescriptionArtifact(SQLModel, table=True):
    __tablename__ = "program_description_artifact"
    __table_args__ = (UniqueConstraint("doc_id", "representation", name="uq_doc_rep"),)

    artifact_id: Optional[int] = Field(default=None, primary_key=True)

    # Identity
    doc_id: str = Field(index=True)  # "1503-27447"
    match_cycle_id: int = Field(index=True)
    program_stream_id: int = Field(foreign_key="program_stream.program_stream_id", index=True)

    # Representation metadata
    representation: str = Field(index=True)  # markdown_v2, html_v2, markdown_enriched, x_section
    source_file: Optional[str] = Field(default=None)

    # Content
    content: str
    content_sha256: Optional[str] = Field(default=None, index=True)

    # Ingest metadata
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
