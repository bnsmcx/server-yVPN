from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    endpoint_count = Column(Integer, default=0)

    endpoints = relationship("Endpoint", back_populates="owner")


class Endpoint(Base):
    __tablename__ = "endpoints"

    droplet_id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    server_ip = Column(String)

    owner = relationship("User", back_populates="endpoints")

