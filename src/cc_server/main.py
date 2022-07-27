"""
fastAPI app for the yourVPN rendezvous server.

Functions -- API Endpoints:
    create_token(token, database) -> Token
    read_tokens(skip, limit, database) -> List[Token]
    read_token(token_id, database) -> Token
    create_endpoint(settings, token, database) -> Endpoint
    get_available_datacenters() -> List[str]
    get_token_status(token, database) -> List[Endpoint]
    delete_endpoint(token, endpoint_name, database) -> None

Functions -- Internal Utility:
    _get_database() -> Session
"""

from typing import List

from fastapi import Depends, FastAPI, Security, HTTPException
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session

from lib import crud, models, schemas, digital_ocean
from lib.database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

test_token = "yoda"
app = FastAPI()
token = APIKeyHeader(name="token", auto_error=False)


def _get_database() -> Session:
    """get and return a database session, ensure it closes"""
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()


def _get_and_validate_token(token: str = Security(token),
                            database: Session = Depends(_get_database)) -> str:
    tokens = []
    for value in database.query(models.Token.token).distinct():
        tokens.append(value[0])
    if token in tokens and not crud.token_is_expired(database, token):
        return token
    else:
        raise HTTPException(status_code=401,
                            detail="Invalid, expired, or missing token.")


@app.post("/tokens/", response_model=schemas.TokenInitialCreationResponse)
def create_token(new_token_request: schemas.TokenCreate,
                 database: Session = Depends(_get_database)):
    """create a new token"""
    return crud.create_token(database, new_token_request)


@app.get("/tokens/", response_model=list[schemas.Token])
def read_tokens(skip: int = 0,
                limit: int = 100,
                database: Session = Depends(_get_database),
                token: str = Depends(_get_and_validate_token)):
    """get and return a list of active Tokens"""
    tokens = crud.get_tokens(database, skip, limit)
    return tokens


@app.post("/create", response_model=schemas.Endpoint)
def create_endpoint(settings: schemas.EndpointCreate,
                    token: str = Depends(_get_and_validate_token),
                    database: Session = Depends(_get_database)):
    """create a new endpoint"""
    if crud.token_has_sufficient_funds(database, token):
        return
        endpoint = crud.create_new_endpoint(database, settings, token)
        return endpoint

    raise HTTPException(status_code=403, detail="Insufficient funds.")


@app.get("/datacenters", response_model=schemas.DataCenters)
def get_available_datacenters(token: str,
                              database: Session = Depends(_get_database)):
    """get a list of available digital ocean datacenters"""
    crud.validate_token(database, token, False)
    return digital_ocean.get_available_datacenters()


@app.get("/status", response_model=List[schemas.Endpoint])
def get_token_status(token: str, database: Session = Depends(_get_database)):
    """get a token's usage summary"""
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
