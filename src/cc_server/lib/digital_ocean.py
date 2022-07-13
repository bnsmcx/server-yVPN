from fastapi import HTTPException

import time
import os

import requests

from . import schemas

DO_TOKEN = os.environ['DIGITALOCEAN_TOKEN']
HEADER = {"Authorization": f"Bearer {DO_TOKEN}"}


def get_available_datacenters() -> schemas.DataCenters:
    regions_raw = requests.get(url="https://api.digitalocean.com/v2/regions",
                               headers=HEADER).json()["regions"]
    regions = []
    for region in regions_raw:
        regions.append(region["slug"])

    return schemas.DataCenters(**{'available': regions})


def create_droplet(endpoint_name: str,
                   ssh_key_id,
                   settings: schemas.EndpointCreate) -> int:
    image_id = 110391971  # TODO: this should not be hardcoded
    request = {
        "name": f"{endpoint_name}",
        "region": f"{settings.region}",
        "size": "s-1vcpu-1gb",
        "image": image_id,
        "ssh_keys": [
            ssh_key_id
        ],
    }

    response = requests.post(json=request,
                             url="https://api.digitalocean.com/v2/droplets",
                             headers=HEADER).json()
    if "droplet" in response:
        return response["droplet"]["id"]
    else:
        raise HTTPException(status_code=404, detail=response)


def set_ssh_key(endpoint_name: str, ssh_pub_key: str) -> int:
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


def delete_ssh_key(ssh_key_id):
    response = requests\
        .delete(url=f"https://api.digitalocean.com/v2/account/keys/{ssh_key_id}",
                headers=HEADER)
    if response.status_code != 204:
        print(response.json())


def extract_ip_from_droplet_json(response: dict) -> str:
    droplet_networks = response["droplet"]["networks"]["v4"]
    for network in droplet_networks:
        if network["type"] == "public":
            return network["ip_address"]


def get_droplet_ip(droplet_id: int) -> str:
    while True:
        response = requests \
            .get(url=f"https://api.digitalocean.com/v2/droplets/{droplet_id}",
                 headers=HEADER)
        if response.status_code != 200:
            print(f"\n***{response.status_code}***\n\n{response.json()}\n")  # DEBUG
            raise HTTPException(status_code=response.status_code,
                                detail=response.json())
        elif response.json()["droplet"]["status"] != "active":
            time.sleep(1)
            continue

        droplet_ip = extract_ip_from_droplet_json(response.json())
        return droplet_ip


def delete_droplet(droplet_id: str):
    requests.delete(url=f"https://api.digitalocean.com/v2/droplets/{droplet_id}",
                    headers=HEADER)
