import os
import requests

from . import schemas

DO_TOKEN = os.environ['DIGITALOCEAN_TOKEN']


def get_available_datacenters() -> schemas.DataCenters:
    header = {"Authorization": f"Bearer {DO_TOKEN}"}
    regions_raw = requests.get(url="https://api.digitalocean.com/v2/regions",
                               headers=header).json()["regions"]
    regions = []
    for region in regions_raw:
        regions.append(region["slug"])

    return schemas.DataCenters(**{'available': regions})


def create_droplet(settings: schemas.EndpointCreate) -> requests.models.Response:
    image_id = 110391971 # TODO: this should not be hardcoded
    request = {
        "name": f"{endpoint_name}",
        "region": f"{settings.region}",
        "size": "s-1vcpu-1gb",
        "image": image_id,
        "ssh_keys": [
            f"{ssh_fingerprint}"
        ],
    }

    header = {"Authorization": f"Bearer {token}"}
    response = requests.post(json=request,
                             url="https://api.digitalocean.com/v2/droplets",
                             headers=header)
