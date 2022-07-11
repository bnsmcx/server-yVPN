from pydantic import BaseModel


class DataCenters(BaseModel):
    available: list[str]


class Endpoint(BaseModel):
    server_ip: str
    
    
class EndpointCreate(BaseModel):
    region: str
    ssh_fingerprint: str


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool

    class Config:
        orm_mode = True

