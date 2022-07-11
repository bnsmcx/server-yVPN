import os
import requests

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from lib import crud, models, schemas, digital_ocean
from lib.database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

DO_TOKEN = os.environ['DIGITALOCEAN_TOKEN']

app = FastAPI()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)


@app.get("/users/", response_model=list[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@app.post("/create", response_model=schemas.Endpoint)
def create_endpoint(endpoint_details: schemas.EndpointCreate,
                    user_token: str,
                    db: Session = Depends(get_db)):
    if not crud.valid_user(db, user_token):
        raise HTTPException(status_code=404, detail="Invalid user token")
    else:
        endpoint = crud.create_new_endpoint(db)
        return endpoint


@app.get("/datacenters", response_model=schemas.DataCenters)
def get_available_datacenters():
    return digital_ocean.get_available_datacenters(DO_TOKEN)
