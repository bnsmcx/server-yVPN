"""
Utility to talk to the digital ocean API

Functions:
    get_available_datacenters() -> schemas.DataCenters
    create_droplet(endpoint_name, ssh_key_id, settings) -> int
    set_ssh_key(endpoint_name, ssh_pub_key) -> int
    delete_ssh_key(ssh_key_id)
    extract_ip_from_droplet_json(dict) -> str
    get_droplet_ip(droplet_id) -> str
    delete_droplet(droplet_id)
"""
import os
import time
import random
from typing import Tuple

import requests
from fastapi import HTTPException

from . import schemas

DO_TOKEN = os.environ['DIGITALOCEAN_TOKEN']
ENDPOINT_IMAGE = os.environ['ENDPOINT_IMAGE']
HEADER = {"Authorization": f"Bearer {DO_TOKEN}"}


def get_available_datacenters() -> schemas.DataCenters:
    """get a list of available digital ocean datacenters"""
    regions_raw = requests.get(url="https://api.digitalocean.com/v2/regions",
                               headers=HEADER).json()["regions"]
    regions = []
    for region in regions_raw:
        regions.append(region["slug"])

    return schemas.DataCenters(**{'available': regions})


def create_droplet(endpoint_name: str,
                   ssh_key_id: int,
                   settings: schemas.EndpointCreate) -> Tuple[int, str]:
    """create a new droplet with token's ssh pubkey, return droplet id"""

    random_region = settings.region == "random"

    image_id = ENDPOINT_IMAGE
    request = {
        "name": f"{endpoint_name}",
        "region": f"{settings.region}",
        "size": "s-1vcpu-1gb",
        "image": image_id,
        "ssh_keys": [
            ssh_key_id
        ],
    }

    while random_region:
        current_region = request["region"]
        request["region"] = random.choice(get_available_datacenters().available)
        request["name"] = request["name"].replace(current_region, request["region"])

        response = requests.post(json=request,
                                 url="https://api.digitalocean.com/v2/droplets",
                                 headers=HEADER)
        if response.status_code != 202:
            continue
        response = response.json()
        return response["droplet"]["id"], response["droplet"]["name"]

    response = requests.post(json=request,
                             url="https://api.digitalocean.com/v2/droplets",
                             headers=HEADER)

    if response.status_code != 202:
        raise HTTPException(status_code=404, detail=response.json())

    response = response.json()
    return response["droplet"]["id"], response["droplet"]["name"]


def set_ssh_key(endpoint_name: str, ssh_pub_key: str) -> int:
    """store an ssh pubkey in digital ocean, return key reference id"""
    request = {
          "public_key": ssh_pub_key,
          "name": endpoint_name
    }
    response = requests.post(json=request,
                             url="https://api.digitalocean.com/v2/account/keys",
                             headers=HEADER)

    if response.status_code != 201:
        raise HTTPException(status_code=404, detail=response.json())
    return response.json()["ssh_key"]["id"]


def delete_ssh_key(ssh_key_id: int):
    """delete an ssh key from digital ocean"""
    response = requests\
        .delete(url=f"https://api.digitalocean.com/v2/account/keys/{ssh_key_id}",
                headers=HEADER)
    if response.status_code != 204:
        print(response.json())


def extract_ip_from_droplet_json(response: dict) -> str:
    """parse json to get the public ip v4 address"""
    droplet_networks = response["droplet"]["networks"]["v4"]
    for network in droplet_networks:
        if network["type"] == "public":
            return network["ip_address"]

    raise HTTPException(status_code=500, detail="Unable to extract droplet ip.")


def get_droplet_ip(droplet_id: int) -> str:
    """wait for a droplet to be created, get and return its IP address"""
    while True:
        response = requests \
            .get(url=f"https://api.digitalocean.com/v2/droplets/{droplet_id}",
                 headers=HEADER)

        if response.status_code != 200:
            print(f"\n***{response.status_code}***\n\n{response.json()}\n")  # DEBUG
            raise HTTPException(status_code=response.status_code,
                                detail=response.json())

        if response.json()["droplet"]["status"] != "active":
            time.sleep(1)
            continue

        droplet_ip = extract_ip_from_droplet_json(response.json())
        return droplet_ip


def delete_droplet(droplet_id: str):
    """delete a droplet"""
    requests.delete(url=f"https://api.digitalocean.com/v2/droplets/{droplet_id}",
                    headers=HEADER)
