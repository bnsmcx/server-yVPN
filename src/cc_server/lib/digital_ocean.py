import requests

from . import schemas

def get_available_datacenters(token: str) -> schemas.DataCenters:
    header = {"Authorization": f"Bearer {token}"}
    regions_raw = requests.get(url="https://api.digitalocean.com/v2/regions",
                               headers=header).json()["regions"]
    regions = []
    for region in regions_raw:
        regions.append(region["slug"])

    return schemas.DataCenters(**{'available': regions})
