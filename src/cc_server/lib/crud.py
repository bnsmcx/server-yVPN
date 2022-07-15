"""
Create, Read, Update, and Delete (CRUD) utilities

Functions:
    get_user(database, user_id) -> models.Token | None
    get_user_by_email(database, email)
    get_user_by_token(database, token) -> models.Token
    get_users(database, skip: int = 0, limit: int = 100)
    is_expired(expiration_date) -> bool
    validate_token(database, token: str) -> bool
    create_user(database, user)
    validate_endpoint_creation_request(settings) -> (bool, str, EndpointCreate)
    update_user_endpoint_count(database, user_id)
    create_new_endpoint(database, settings, token) -> Endpoint
    get_user_endpoints(database, token) -> List[Endpoint]
    delete_endpoint(token, endpoint_name, database)
"""

import random
from datetime import timedelta, datetime, timezone
from typing import Tuple, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import models, schemas, digital_ocean


def get_user(database: Session, user_id: int) -> models.Token | None:
    """get a user by id"""
    return database.query(models.Token).filter(models.Token.id == user_id).first()


def get_user_by_email(database: Session, email: str) -> models.Token | None:
    """get a user by email"""
    return database.query(models.Token).filter(models.Token.email == email).first()


def get_user_by_token(database: Session, user_token: str) -> models.Token | None:
    """get a user by new_token_request"""
    user = database.query(models.Token) \
        .filter(models.Token.token == user_token) \
        .first()
    return user


def get_users(database: Session,
              skip: int = 0,
              limit: int = 100) -> List[models.Token]:
    """get a list of all users, skip and limit parameters slice"""
    return database.query(models.Token).offset(skip).limit(limit).all()


def is_expired(expiration_date: str):
    """check if we are past an expiration date"""
    expiration_date = datetime.strptime(expiration_date, "%d-%B-%Y %H:%M:%S UTC")
    return datetime.now(tz=timezone.utc) > expiration_date.replace(tzinfo=timezone.utc)


def validate_token(database: Session, token: str):
    """check if a token is valid"""
    query_result = database.query(models.Token) \
        .filter(models.Token.token == token) \
        .first()

    if not isinstance(query_result, models.Token):
        raise HTTPException(status_code=404, detail="Token not found.")
    if query_result.funds_available <= 0:
        raise HTTPException(status_code=401, detail="Insufficient funds.")
    if is_expired(query_result.expiration):
        raise HTTPException(status_code=401, detail="Token is expired.")


def get_expiration_date(days_till_expiration: int) -> str:
    """calculate the expiration date"""
    now = datetime.now(tz=timezone.utc)
    new_date = now + timedelta(days=days_till_expiration)

    return new_date.strftime("%d-%B-%Y %H:%M:%S UTC")


def create_token(database: Session,
                 request: schemas.TokenCreate) -> schemas.TokenInitialCreationResponse:
    """create a new user"""
    new_token = f"cellar_door{random.random()}"  # TODO: implement new_token_request creation
    db_token_entry = models.Token(token=new_token,
                                  funds_available=request.funds,
                                  expiration=get_expiration_date(request.days_till_expiration))

    database.add(db_token_entry)
    database.commit()
    database.refresh(db_token_entry)
    return schemas.TokenInitialCreationResponse(token=db_token_entry.token,
                                                funds_available=db_token_entry.funds_available,
                                                expiration=db_token_entry.expiration)


def validate_endpoint_creation_request(
        settings: schemas.EndpointCreate) -> Tuple[bool, str, schemas.EndpointCreate]:
    """check region and ssh keys are valid, set random region if applicable"""
    available_datacenters = digital_ocean.get_available_datacenters().available
    if settings.region != "random" and settings.region not in available_datacenters:
        return (False,
                f"Datacenter '{settings.region}' not available."
                f" Try 'random' or one of these: {sorted(available_datacenters)}",
                settings)
    if len(settings.ssh_pub_key) < 1:
        return False, "SSH public key required.", settings
    if settings.region == "random":
        settings.region = random.choice(available_datacenters)
    return True, "", settings


def update_user_endpoint_count(database: Session, user_id: int) -> None:
    """count and store the number of endpoints associated with a user"""
    user = database.query(models.Token).filter(models.Token.id == user_id).first()
    user.endpoint_count = len(user.endpoints)
    database.add(user)
    database.commit()
    database.refresh(user)


def create_new_endpoint(database: Session,
                        settings: schemas.EndpointCreate,
                        user_token: str) -> schemas.Endpoint:
    """create a new endpoint"""

    # get user profile, validate the new endpoint settings
    user = database.query(models.Token).filter(models.Token.token == user_token).first()
    valid_request, error, settings = validate_endpoint_creation_request(settings)
    if not valid_request:
        raise HTTPException(status_code=404, detail=error)

    # name endpoint, set the ssh key, request droplet creation, delete ssh key
    endpoint_name = f"{user.id}-{user.endpoint_count + 1}-{settings.region}"
    ssh_key_id = digital_ocean.set_ssh_key(endpoint_name, settings.ssh_pub_key)
    try:
        droplet_id = digital_ocean.create_droplet(endpoint_name, ssh_key_id, settings)
    finally:
        digital_ocean.delete_ssh_key(ssh_key_id)

    # get new endpoint's ip, create Endpoint obj
    endpoint_ip = digital_ocean.get_droplet_ip(droplet_id)
    database_endpoint = models.Endpoint(server_ip=endpoint_ip,
                                        owner_id=user.id,
                                        endpoint_name=endpoint_name,
                                        droplet_id=droplet_id)

    # add to database, update user's endpoint count, and return Endpoint
    database.add(database_endpoint)
    database.commit()
    database.refresh(database_endpoint)
    update_user_endpoint_count(database, user.id)
    return schemas.Endpoint(server_ip=database_endpoint.server_ip,
                            endpoint_name=database_endpoint.endpoint_name)


def get_user_endpoints(database: Session, user_token: str) -> List[schemas.Endpoint]:
    """return a list of the user's endpoints"""
    user = get_user_by_token(database, user_token)
    return user.endpoints


def delete_endpoint(user_token, endpoint_name, database):
    """delete a user's endpoint by name"""
    endpoint = database.query(models.Endpoint) \
        .filter(models.Endpoint.endpoint_name == endpoint_name)
    droplet_id = endpoint.first().droplet_id
    digital_ocean.delete_droplet(droplet_id)
    endpoint.delete()
    update_user_endpoint_count(database, get_user_by_token(database, user_token).id)
