"""
fastAPI app for the yourVPN rendezvous server.

Functions -- API Endpoints:
    create_user(user, database) -> User
    read_users(skip, limit, database) -> List[User]
    read_user(user_id, database) -> User
    create_endpoint(settings, user_token, database) -> Endpoint
    get_available_datacenters() -> List[str]
    get_user_status(user_token, database) -> List[Endpoint]
    delete_endpoint(user_token, endpoint_name, database) -> None

Functions -- Internal Utility:
    _get_database() -> Session
"""

from typing import List

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from lib import crud, models, schemas, digital_ocean
from lib.database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


def _get_database():
    """get and return a database session, ensure it closes"""
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()


@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, database: Session = Depends(_get_database)):
    """create a new user"""
    database_user = crud.get_user_by_email(database, user.email)
    if database_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(database, user)


@app.get("/users/", response_model=list[schemas.User])
def read_users(skip: int = 0,
               limit: int = 100,
               database: Session = Depends(_get_database)):
    """get and return a list of users"""
    users = crud.get_users(database, skip, limit)
    return users


@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, database: Session = Depends(_get_database)):
    """return a specific user"""
    database_user = crud.get_user(database, user_id)
    if database_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return database_user


@app.post("/create", response_model=schemas.Endpoint)
def create_endpoint(settings: schemas.EndpointCreate,
                    user_token: str,
                    database: Session = Depends(_get_database)):
    """create a new endpoint"""
    if not crud.valid_user_token(database, user_token):
        raise HTTPException(status_code=401, detail="Invalid user token")
    endpoint = crud.create_new_endpoint(database, settings, user_token)
    return endpoint


@app.get("/datacenters", response_model=schemas.DataCenters)
def get_available_datacenters(user_token: str,
                              database: Session = Depends(_get_database)):
    """get a list of available digital ocean datacenters"""
    if not crud.valid_user_token(database, user_token):
        raise HTTPException(status_code=401, detail="Invalid user token.")
    return digital_ocean.get_available_datacenters()


@app.get("/status", response_model=List[schemas.Endpoint])
def get_user_status(user_token: str, database: Session = Depends(_get_database)):
    """get a user's usage summary"""
    if not crud.valid_user_token(database, user_token):
        raise HTTPException(status_code=401, detail="Invalid user token")
    user_endpoints = crud.get_user_endpoints(database, user_token)
    return user_endpoints


@app.delete("/endpoint")
def delete_endpoint(user_token: str,
                    endpoint_name: str,
                    database: Session = Depends(_get_database)):
    """delete an endpoint"""
    if not crud.valid_user_token(database, user_token):
        raise HTTPException(status_code=401, detail="Invalid user token.")
    crud.delete_endpoint(user_token, endpoint_name, database)
