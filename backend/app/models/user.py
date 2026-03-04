from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # soft credit system (default 1000 tokens)
    credits = Column(Integer, nullable=False, server_default="1000")
    # cumulative usage statistics
    total_tokens_used = Column(Integer, nullable=False, server_default="0")
    total_cost = Column(Float, nullable=False, server_default="0")
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True, nullable=True)  # tenant association
