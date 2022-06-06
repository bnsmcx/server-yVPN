# yourVPN

This project is intended to be a Minimum Viable Product that demonstrates a user's ability to simply spawn, connect to, and kill VPN endpoints on demand.  What sets this apart from most VPN offerings is that the endpoints only service a single user and only exist for the duration of the session.  While this is relatively simple for users to manually do, this project automates it and provides a good platform for scaling.

The developmental focus will be on the code for the endpoints and the command and control server.  At this point the client is meant to be very minimal as it will potentially be expanded to multiple clients to support different use cases.

## Envisioned Flow

1] User sets an environment variable with their token
2] User runs the `yvpn-client connect` command from their terminal
3] `yvpn-client` calls the command and control server (`cc-server`) `yourvpn.info/get-endpoint`
4] `cc-server` calls the digital ocean API to create a new `vpn-endpoint`
5] `cc-server` calls the digital ocean API to get the new `vpn-endpoint`'s IP address
6] `cc-server` returns the new `vpn-endpoint`'s IP address to `yvpn-client`
7] `yvpn-client` calls the `vpn-endpoint`'s `/key-exchange` endpoint
8] `vpn-endpoint` validate's the user's token with the `cc-server`
9] `vpn-endpoint` configures and activates the wireguard server
10] `vpn-endpoint` returns `wg0.conf` to `yvpn-client`
11] `yvpn-client` finalizes `wg0.conf` and initiates the wg tunnel

***User completes their session.***

12] User runs the `yvpn-client disconnect` command from their terminal
13] `yvpn-client` calls the `cc-server`'s `/kill` endpoint
14] `cc-server` calls digital ocean api and kills all instances of `vpn-endpoint`
