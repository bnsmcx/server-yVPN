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


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    endpoint_count: int
    endpoints: List[Endpoint]

    class Config:
        orm_mode = True

