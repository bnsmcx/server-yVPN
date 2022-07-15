"""
fastAPI app for the yourVPN rendezvous server.

Functions -- API Endpoints:
    create_user(user, database) -> Token
    read_users(skip, limit, database) -> List[Token]
    read_user(user_id, database) -> Token
    create_endpoint(settings, token, database) -> Endpoint
    get_available_datacenters() -> List[str]
    get_user_status(token, database) -> List[Endpoint]
    delete_endpoint(token, endpoint_name, database) -> None

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


@app.post("/tokens/", response_model=schemas.TokenInitialCreationResponse)
def create_token(new_token_request: schemas.TokenCreate, database: Session = Depends(_get_database)):
    """create a new new_token_request"""
    return crud.create_token(database, new_token_request)


@app.get("/tokens/", response_model=list[schemas.Token])
def read_tokens(skip: int = 0,
               limit: int = 100,
               database: Session = Depends(_get_database)):
    """get and return a list of users"""
    users = crud.get_users(database, skip, limit)
    return users


@app.post("/create", response_model=schemas.Endpoint)
def create_endpoint(settings: schemas.EndpointCreate,
                    token: str,
                    database: Session = Depends(_get_database)):
    """create a new endpoint"""
    crud.validate_token(database, token, True)
    endpoint = crud.create_new_endpoint(database, settings, token)
    return endpoint


@app.get("/datacenters", response_model=schemas.DataCenters)
def get_available_datacenters(user_token: str,
                              database: Session = Depends(_get_database)):
    """get a list of available digital ocean datacenters"""
    crud.validate_token(database, user_token, False)
    return digital_ocean.get_available_datacenters()


@app.get("/status")
def get_token_status(token: str, database: Session = Depends(_get_database)):
    """get a user's usage summary"""
    crud.validate_token(database, token, False)
    endpoints = crud.get_endpoints_by_token(database, token)
    return endpoints


@app.delete("/endpoint")
def delete_endpoint(token: str,
                    endpoint_name: str,
                    database: Session = Depends(_get_database)):
    """delete an endpoint"""
    crud.validate_token(database, token, False)
    crud.delete_endpoint(token, endpoint_name, database)
