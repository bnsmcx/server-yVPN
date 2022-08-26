"""
Create, Read, Update, and Delete (CRUD) utilities
"""
import multiprocessing
import secrets
import sys
import time
from datetime import timedelta, datetime, timezone
from typing import Tuple, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import models, schemas, digital_ocean, database


def get_token_db_record(database: Session, token: str) -> models.Token | None:
    """get a token record from the database"""
    token = database.query(models.Token) \
        .filter(models.Token.token == token) \
        .first()
    return token


def get_tokens(database: Session,
               skip: int = 0,
               limit: int = 100) -> List[models.Token]:
    """get a list of all tokens, skip and limit parameters slice"""
    return database.query(models.Token).offset(skip).limit(limit).all()


def token_is_expired(database: Session, token: str):
    """check if we are past an expiration date"""
    query = database.query(models.Token) \
        .filter(models.Token.token == token) \
        .first()

    token_expiration = datetime\
        .strptime(query.expiration, "%d-%B-%Y %H:%M:%S UTC")\
        .replace(tzinfo=timezone.utc)
    today = datetime.now(tz=timezone.utc)

    return today > token_expiration


def get_expiration_date(days_till_expiration: int) -> str:
    """calculate the expiration date"""
    now = datetime.now(tz=timezone.utc)
    new_date = now + timedelta(days=days_till_expiration)

    return new_date.strftime("%d-%B-%Y %H:%M:%S UTC")


def create_token(database: Session,
                 request: schemas.TokenCreate) -> schemas.TokenInitialCreationResponse:
    """create a new token"""
    new_token = secrets.token_hex()
    db_token_entry = models.Token(token=new_token,
                                  admin=request.admin,
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
    return True, "", settings


def update_token_endpoint_count(database: Session, token: str) -> None:
    """count and store the number of endpoints associated with a token"""
    db_token_entry = database.query(models.Token)\
        .filter(models.Token.token == token).first()
    db_token_entry.endpoint_count = len(db_token_entry.endpoints)
    database.add(db_token_entry)
    database.commit()
    database.refresh(db_token_entry)


def create_new_endpoint(database: Session,
                        settings: schemas.EndpointCreate,
                        token: str) -> schemas.Endpoint:
    """create a new endpoint"""

    # get token db entry, validate the new endpoint settings
    token_db_entry = database.query(models.Token)\
        .filter(models.Token.token == token).first()
    valid_request, error, settings = validate_endpoint_creation_request(settings)
    if not valid_request:
        raise HTTPException(status_code=404, detail=error)

    # name endpoint, set the ssh key, request droplet creation, delete ssh key
    abbreviated_token = token_db_entry.token[-6:]
    endpoint_count = token_db_entry.endpoint_count + 1
    datacenter = settings.region
    endpoint_name = f"{abbreviated_token}-{endpoint_count}-{datacenter}"
    ssh_key_id = digital_ocean.set_ssh_key(endpoint_name, settings.ssh_pub_key)
    try:
        droplet_id, endpoint_name = digital_ocean\
            .create_droplet(endpoint_name, ssh_key_id, settings)
    finally:
        digital_ocean.delete_ssh_key(ssh_key_id)

    # get new endpoint's ip, create Endpoint obj
    endpoint_ip = digital_ocean.get_droplet_ip(droplet_id)
    database_endpoint = models.Endpoint(server_ip=endpoint_ip,
                                        owner_id=token_db_entry.token,
                                        endpoint_name=endpoint_name,
                                        droplet_id=droplet_id)

    # add to database, update token's endpoint count, and return Endpoint
    database.add(database_endpoint)
    database.commit()
    database.refresh(database_endpoint)
    update_token_endpoint_count(database, token_db_entry.token)
    return schemas.Endpoint(server_ip=database_endpoint.server_ip,
                            endpoint_name=database_endpoint.endpoint_name)


def get_endpoints_by_token(database: Session, token: str) -> List[schemas.Endpoint]:
    """return a list of the token's endpoints"""
    token = get_token_db_record(database, token)
    return token.endpoints


def delete_token(token: str, database: Session):
    """delete a token"""
    token_db_entry = database.query(models.Token)\
        .filter(models.Token.token == token)

    # using count() as bool here, should only ever be 1 or 0
    if token_db_entry.count():
        for endpoint in token_db_entry.one().endpoints:
            delete_endpoint(token, endpoint.endpoint_name, database)
        token_db_entry.delete()
        database.commit()
    else:
        raise HTTPException(status_code=422,
                            detail="Token not found.")


def delete_endpoint(token, endpoint_name, database):
    """delete a token's endpoint by name"""
    endpoint = database.query(models.Endpoint) \
        .filter(models.Endpoint.endpoint_name == endpoint_name,
                models.Endpoint.owner ==
                get_token_db_record(database, token))

    if not isinstance(endpoint.first(), models.Endpoint):
        raise HTTPException(status_code=422,
                            detail="Endpoint not found.  Either the name is"
                                   " wrong or it isn't associated with your token.")

    droplet_id = endpoint.first().droplet_id
    digital_ocean.delete_droplet(droplet_id)
    endpoint.delete()
    update_token_endpoint_count(database,
                                get_token_db_record(database, token).token)
    database.commit()


def token_has_sufficient_funds(database: Session, token: str):
    query_result = database.query(models.Token) \
        .filter(models.Token.token == token) \
        .first()
    if query_result is None or query_result.funds_available <= 0:
        return False
    return True


def billing_worker():
    """Updates the token's funds once per minute"""
    digital_ocean_hourly_rate = 0.00893
    yvpn_markup = 2
    cost_per_minute = (digital_ocean_hourly_rate * yvpn_markup)/60
    while True:
        try:
            db = database.SessionLocal()
            models.Base.metadata.create_all(bind=database.engine)
            tokens = get_tokens(db)
            for token in tokens:
                entry = db.query(models.Token) \
                    .filter(models.Token.token == token.token).first()
                new_charge = cost_per_minute * entry.endpoint_count
                if (entry.funds_available - new_charge) >= 0:
                    entry.funds_available = entry.funds_available - new_charge
                    db.add(entry)
                    db.commit()
                    db.refresh(entry)
                else:
                    delete_token(token, db)
            time.sleep(60)

        except Exception as e:
            print(f"{type(e)}\n{e.args}")
            sys.exit(1)


def start_billing_worker():
    """Start a subprocess that """
    worker = multiprocessing.Process(target=billing_worker)
    worker.start()
