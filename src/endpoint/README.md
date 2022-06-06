# yourVPN endpoint

This is the endpoint or exit node of the yourVPN framework.  It consists of code to handle the following:

1] Startup script that runs on droplet creation
  - Performs `apt update && apt upgrade -y`
  - Validates that fastAPI service is running
  - Validates that wireguard is running
  - validates that the ufw firewall is configured and enabled

2] fastAPI server with one endpoint: `/key_exchange`
  - `POST` request requires:
    - User's bearer token
    - User's client wireguard public key
    - User's requested tunnel ip address

  - Actions performed:
    - validate user's token with command and control server
    - set appropriate server ip based on user's requested client IP
    - add user's public key and ip as wireguard peer and activate wireguard
    - create `wg0.conf` file for user with templating for client to fill clinet's private key

  - Returns:
    - `wg0.conf`


