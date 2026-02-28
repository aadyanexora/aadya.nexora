from sqlalchemy import Column, Integer, Text, String
from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    # optional human-readable name or source identifier (e.g. filename)
    name = Column(String, nullable=True)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, index=True)
    # ordinal index of chunk within document
    chunk_index = Column(Integer, index=True)
    content = Column(Text, nullable=False)
