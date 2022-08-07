"""
Pydantic datamodels

Classes (models):
    DataCenters
    Endpoint
    EndpointCreate
    UserBase
    UserCreate
    Token
"""
# pylint: skip-file

from typing import List

from pydantic import BaseModel


class DataCenters(BaseModel):
    available: list[str]


class Endpoint(BaseModel):
    server_ip: str
    endpoint_name: str

    class Config:
        orm_mode = True
    
    
class EndpointCreate(BaseModel):
    region: str
    ssh_pub_key: str


class TokenCreate(BaseModel):
    funds: float
    days_till_expiration: int


class TokenInitialCreationResponse(BaseModel):
    funds_available: float
    expiration: str


class Token(BaseModel):
    token: str
    is_active: bool
    funds_available: float
    expiration: str
    endpoint_count: int
    endpoints: List[Endpoint]

    class Config:
        orm_mode = True

