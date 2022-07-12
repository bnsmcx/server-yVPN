import random

from fastapi import HTTPException
from typing import Tuple

from sqlalchemy.orm import Session

from . import models, schemas, digital_ocean


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def valid_user(db, user_token) -> bool:
    query_result = db.query(models.User).filter(models.User.token == user_token).first()
    return isinstance(query_result, models.User)


def create_user(db: Session, user: schemas.UserCreate):
    fake_hashed_password = user.password + "notreallyhashed"
    db_user = models.User(email=user.email, token="yeet",
                          hashed_password=fake_hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def validate_endpoint_creation_request(
        settings: schemas.EndpointCreate) -> Tuple[bool, str, schemas.EndpointCreate]:
    available_datacenters = digital_ocean.get_available_datacenters().available
    if settings.region != "random" and settings.region not in available_datacenters:
        return (False,
                f"Datacenter '{settings.region}' not available."
                f" Try 'random' or one of these: {sorted(available_datacenters)}",
                settings)
    if len(settings.ssh_pub_key) < 1:
        return (False, "SSH public key required.", settings)
    if settings.region == "random":
        settings.region = random.choice(available_datacenters)
    return (True, "", settings)


def create_new_endpoint(db: Session,
                        settings: schemas.EndpointCreate,
                        user_token: str) -> schemas.Endpoint:
    # validate the new endpoint settings
    valid_request, error, settings = validate_endpoint_creation_request(settings)
    if not valid_request:
        raise HTTPException(status_code=404, detail=error)

    # get user_id and endpoint count for name
    user = db.query(models.User).filter(models.User.token == user_token).first()
    endpoint_name = f"{user.id}-{user.endpoint_count}-{settings.region}"

    # set the ssh key for endpoint creation
    ssh_key_id = digital_ocean.set_ssh_key(endpoint_name, settings.ssh_pub_key)

    # send the creation request to DO, get the droplet id
    droplet_id = digital_ocean.create_droplet(endpoint_name, ssh_key_id, settings)

    # delete the ssh key from DO
    digital_ocean.delete_ssh_key(ssh_key_id)

    # request status of creation

    # await creation finishing

    # return new endpoint's IP in schemas.Endpoint
    pass
