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
        settings: schemas.EndpointCreate) -> Tuple[bool, str]:
    available_datacenters = digital_ocean.get_available_datacenters().available
    print(settings.region != "random")
    if settings.region != "random" and settings.region not in available_datacenters:
        return (False, f"Datacenter '{settings.region}' not available."
                       f" Try 'random' or one of these: {sorted(available_datacenters)}")
    if len(settings.ssh_fingerprint) < 1:
        return (False, "SSH fingerprint required.")
    return (True, "")


def create_new_endpoint(db: Session,
                        settings: schemas.EndpointCreate) -> schemas.Endpoint:
    # validate the new endpoint settings
    valid_request, error = validate_endpoint_creation_request(settings)
    if not valid_request:
        raise HTTPException(status_code=404, detail=error)

    # send the creation request to DO

    # await the droplet id, indicating it is being created

    # request status of creation

    # await creation finishing

    # return new endpoint's IP in schemas.Endpoint
    pass
