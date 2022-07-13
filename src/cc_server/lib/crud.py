import random

from fastapi import HTTPException
from typing import Tuple

from sqlalchemy.orm import Session

from . import models, schemas, digital_ocean


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


# def get_user_by_token(db: Session, user_token: str) -> int:
#     user = db.query(models.User).filter(models.User.token == user_token).first()
#     return user.id


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def valid_user(db: Session, user_token: str) -> bool:
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
    # get user profile, validate the new endpoint settings
    user = db.query(models.User).filter(models.User.token == user_token).first()
    valid_request, error, settings = validate_endpoint_creation_request(settings)
    if not valid_request:
        raise HTTPException(status_code=404, detail=error)

    # name endpoint, set the ssh key, request droplet creation, delete ssh key
    endpoint_name = f"{user.id}-{user.endpoint_count}-{settings.region}"
    ssh_key_id = digital_ocean.set_ssh_key(endpoint_name, settings.ssh_pub_key)
    droplet_id = digital_ocean.create_droplet(endpoint_name, ssh_key_id, settings)
    digital_ocean.delete_ssh_key(ssh_key_id)

    # get new endpoint's ip, create Endpoint obj, add to db and return it
    endpoint_ip = digital_ocean.get_droplet_ip(droplet_id)
    db_endpoint = models.Endpoint(server_ip=endpoint_ip,
                                  owner_id=user.id)
    db.add(db_endpoint)
    db.commit()
    db.refresh(db_endpoint)
    return schemas.Endpoint(server_ip=db_endpoint.server_ip)
