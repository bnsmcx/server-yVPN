"""
sqlalchemy models

Classes:
    Token
    Endpoint
"""
# pylint: skip-file

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float
from sqlalchemy.orm import relationship

from .database import Base


class Token(Base):
    """ORM model for a Token"""
    __tablename__ = "tokens"

    token = Column(String, primary_key=True, index=True)
    is_active = Column(Boolean, default=True)
    funds_available = Column(Float)
    expiration = Column(String)
    endpoint_count = Column(Integer, default=0)

    endpoints = relationship("Endpoint", back_populates="owner")


class Endpoint(Base):
    """ORM model for an Endpoint"""
    __tablename__ = "endpoints"

    endpoint_name = Column(String)
    server_ip = Column(String)
    droplet_id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("tokens.token"))

    owner = relationship("Token", back_populates="endpoints")
