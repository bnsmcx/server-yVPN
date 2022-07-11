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
