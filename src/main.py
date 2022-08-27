"""
fastAPI app for the yourVPN rendezvous server.
"""

from typing import List

from fastapi import Depends, FastAPI, Security, HTTPException
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session

from lib import crud, models, schemas, digital_ocean
from lib.database import SessionLocal, engine
from lib import util

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
crud.start_billing_worker()
token = APIKeyHeader(name="token", auto_error=False)


def _get_database() -> Session:
    """get and return a database session, ensure it closes"""
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()


def _get_and_validate_user_token(token: str = Security(token),
                                 database: Session = Depends(_get_database)) -> str:
    if valid_token := database.query(models.Token).get(token):
        return valid_token.token
    else:
        raise HTTPException(status_code=401,
                            detail="Invalid, expired, or missing token.")


def _get_and_validate_admin_token(token: str = Security(token),
                                  database: Session = Depends(_get_database)):
    if valid_token := database.query(models.Token).get(token):
        if not valid_token.admin:
            raise HTTPException(status_code=401,
                                detail="Admin token required for this action.")
    else:
        raise HTTPException(status_code=401,
                            detail="Invalid, expired, or missing token.")


@app.post("/tokens", response_model=schemas.TokenInitialCreationResponse)
def create_token(new_token_request: schemas.TokenCreate,
                 admin_token: str = Depends(_get_and_validate_admin_token),
                 database: Session = Depends(_get_database)):
    """create a new token"""
    return crud.create_token(database, new_token_request)


@app.get("/tokens", response_model=list[schemas.Token])
def read_tokens(skip: int = 0,
                limit: int = 100,
                database: Session = Depends(_get_database),
                admin_token: str = Depends(_get_and_validate_admin_token)):
    """get and return a list of active Tokens"""
    tokens = crud.get_tokens(database, skip, limit)
    return tokens


@app.delete("/tokens")
def delete_token(token_to_delete: str,
                 admin_token: str = Depends(_get_and_validate_admin_token),
                 database: Session = Depends(_get_database)):
    """delete an endpoint"""
    crud.delete_token(token_to_delete, database)


@app.post("/create", response_model=schemas.Endpoint)
def create_endpoint(settings: schemas.EndpointCreate,
                    token: str = Depends(_get_and_validate_user_token),
                    database: Session = Depends(_get_database)):
    """create a new endpoint"""
    if crud.token_has_sufficient_funds(database, token):
        endpoint = crud.create_new_endpoint(database, settings, token)
        return endpoint

    raise HTTPException(status_code=403, detail="Insufficient funds.")


@app.get("/datacenters", response_model=schemas.DataCenters)
def get_available_datacenters(token: str = Depends(_get_and_validate_user_token)):
    """get a list of available digital ocean datacenters"""
    return digital_ocean.get_available_datacenters()


@app.get("/status", response_model=schemas.Status)
def get_token_status(token: str = Depends(_get_and_validate_user_token),
                     database: Session = Depends(_get_database)):
    """get a token's usage summary"""
    record = crud.get_token_db_record(database, token)
    funds = record.funds_available
    endpoints = record.endpoint_count
    active, estimate = util.estimate_fund_depletion(funds, endpoints)
    status = schemas.Status(
        endpoints=crud.get_endpoints_by_token(database, token),
        funds=funds,
        # TODO: set to expiration if sooner than est depletion date
        est_depletion=estimate if active else 9999
    )
    return status


@app.delete("/endpoint")
def delete_endpoint(endpoint_name: str,
                    token: str = Depends(_get_and_validate_user_token),
                    database: Session = Depends(_get_database)):
    """delete an endpoint"""
    crud.delete_endpoint(token, endpoint_name, database)
