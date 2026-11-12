"""Project vector collection indexing registry model (`project_vector_indexes`)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.organisation import Organisation
    from app.models.project import Project


class ProjectVectorIndex(Base):
    """Project-isolated vector collection metadata record in PostgreSQL."""

    __tablename__ = "project_vector_indexes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    collection_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
    )
    embedding_model: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="nomic-embed-text",
        server_default="nomic-embed-text",
    )
    embedding_dimension: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=768,
        server_default="768",
    )
    collection_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="v1",
        server_default="v1",
    )
    index_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ready",
        server_default="ready",
    )
    last_indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organisation: Mapped[Organisation] = relationship("Organisation")
    project: Mapped[Project] = relationship("Project")
