"""
Create, Read, Update, and Delete (CRUD) utilities

Functions:
    get_user(database, user_id) -> models.User | None
    get_user_by_email(database, email)
    get_user_by_token(database, user_token) -> models.User
    get_users(database, skip: int = 0, limit: int = 100)
    valid_user(database, user_token: str) -> bool
    create_user(database, user)
    validate_endpoint_creation_request(settings) -> (bool, str, EndpointCreate)
    update_user_endpoint_count(database, user_id)
    create_new_endpoint(database, settings, user_token) -> Endpoint
    get_user_endpoints(database, user_token) -> List[Endpoint]
    delete_endpoint(user_token, endpoint_name, database)
"""

import random
from typing import Tuple, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import models, schemas, digital_ocean


def get_user(database: Session, user_id: int) -> models.User | None:
    """get a user by id"""
    return database.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(database: Session, email: str) -> models.User | None:
    """get a user by email"""
    return database.query(models.User).filter(models.User.email == email).first()


def get_user_by_token(database: Session, user_token: str) -> models.User | None:
    """get a user by token"""
    user = database.query(models.User) \
        .filter(models.User.token == user_token) \
        .first()
    return user


def get_users(database: Session,
              skip: int = 0,
              limit: int = 100) -> List[models.User]:
    """get a list of all users, skip and limit parameters slice"""
    return database.query(models.User).offset(skip).limit(limit).all()


def valid_user_token(database: Session, user_token: str) -> bool:
    """check if a user token is valid"""
    query_result = database.query(models.User) \
        .filter(models.User.token == user_token) \
        .first()
    return isinstance(query_result, models.User)


def create_user(database: Session, user: schemas.UserCreate) -> models.User:
    """create a new user"""
    fake_hashed_password = user.password + "notreallyhashed"
    database_user = models.User(email=user.email, token="yeet",
                                hashed_password=fake_hashed_password)
    database.add(database_user)
    database.commit()
    database.refresh(database_user)
    return database_user


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
    user = database.query(models.User).filter(models.User.id == user_id).first()
    user.endpoint_count = len(user.endpoints)
    database.add(user)
    database.commit()
    database.refresh(user)


def create_new_endpoint(database: Session,
                        settings: schemas.EndpointCreate,
                        user_token: str) -> schemas.Endpoint:
    """create a new endpoint"""

    # get user profile, validate the new endpoint settings
    user = database.query(models.User).filter(models.User.token == user_token).first()
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
