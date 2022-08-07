# Command and Control Server

This server is the go-between between the client and the digital ocean API.  It handles the creation and destruction of the endpoints based on the client's requests.   It consists of the following endpoints:

## `/get-endpoint`

### Accepts:

  - User's bearer token
  - Requested endpoint location (optional)

### Actions:
  
  - Validate token
  - Validate requested endpoint location
  - Call digital ocean API to create endpoint
  - Get public IP address of newly created endpoint

### Returns:

  - New endpoint's public IP address

## `/kill`

  - Kills the current endpoint

## `/validate`

  - Validates a user's token, called by endpoint during key exchange with client to validate client

