#!/usr/bin/env python3

import requests

url = "http://165.22.102.167:8000/key-exchange"
data = '{"pubkey": "token", "ip": "10.0.0.2"}'
header = "\"Content-Type: application/json\""

request = requests.post(url=url, data=data)

print(request.json())
