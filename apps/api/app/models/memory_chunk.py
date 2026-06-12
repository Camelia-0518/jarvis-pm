"""Memory chunk model for semantic search"""

from sqlalchemy import Column, String, DateTime, Text, Integer, Index
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class MemoryChunk(Base):
    """Semantic memory chunk with embedding vector"""
    __tablename__ = "memory_chunks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_type = Column(String, nullable=False, index=True)  # prd, project, knowledge, etc.
    source_id = Column(String, nullable=False, index=True)    # prd_id, project_id, etc.
    chunk_index = Column(Integer, nullable=False, default=0)  # position in document
    content = Column(Text, nullable=False)                     # text content
    embedding = Column(Text, nullable=True)                    # JSON array of floats
    chunk_metadata = Column(Text, nullable=True)               # JSON metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_memory_chunks_source", "source_type", "source_id"),
        Index("idx_memory_chunks_created", "created_at"),
    )