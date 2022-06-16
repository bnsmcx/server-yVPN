#!/usr/bin/env python

from pathlib import Path
from paramiko import SSHClient
from getpass import getpass
import typer
import os

app = typer.Typer()


@app.command()
def create():
    """CREATE a new VPN endpoint"""
    # TODO: implement Digital Ocean API creation of droplet
    server_ip = "146.190.228.155"
    client_ip = "10.0.0.2"  # TODO: let the user set this

    refresh_client_keys()
    server_public_key = server_key_exchange(server_ip, client_ip)
    configure_wireguard_client(server_public_key, server_ip, client_ip)


@app.command()
def connect():
    """CONNECT to your active endpoint"""
    pass


@app.command()
def disconnect():
    """DISCONNECT from your endpoint"""
    pass


@app.command()
def destroy():
    """permanently DESTROY your endpoint"""
    pass


@app.command()
def status():
    """display connection, usage and endpoint info"""
    pass


def server_key_exchange(server_ip: str, client_ip: str) -> str:
    # create ssh client and connect
    ssh = SSHClient()
    ssh.load_system_host_keys()
    passphrase = getpass(prompt="id_rsa passphrase: ")
    ssh.connect(server_ip, port=22, username="root", passphrase=passphrase)

    # activate client on server
    client_public_key = Path("/etc/wireguard/public.key").read_text().strip()
    command = f"wg set wg0 peer {client_public_key} allowed-ips {client_ip}"
    ssh.exec_command(command)

    # get and return server public key
    (stdin, stdout, stderr) = ssh.exec_command("cat /etc/wireguard/public.key")
    server_public_key = stdout.read().decode().strip()
    return server_public_key


def refresh_client_keys():
    # delete old wireguard keys and config
    os.system("sudo rm /etc/wireguard/*")

    # generate fresh client keys
    os.system("wg genkey | " + \
              "sudo tee /etc/wireguard/private.key | " + \
              "wg pubkey | sudo tee /etc/wireguard/public.key | " + \
              "echo > /dev/null")  # hack: can't seem to write directly to public.key

    # lockdown key files
    os.system("sudo chmod 600 /etc/wireguard/private.key && " + \
              "sudo chmod 644 /etc/wireguard/public.key")


def get_client_private_key() -> str:
    os.system("sudo chmod 644 /etc/wireguard/private.key")
    with open("/etc/wireguard/private.key") as f:
        private_key = f.read().strip()
    os.system("sudo chmod 600 /etc/wireguard/private.key")
    return private_key


def configure_wireguard_client(server_public_key: str,
                               server_ip: str, client_ip: str) -> None:
    config = ("[Interface]",
              f"PrivateKey = {get_client_private_key()}",
              f"Address = {client_ip}/24",
              "\n",
              "[Peer]",
              f"PublicKey = {server_public_key}",
              f"Endpoint = {server_ip}:51820",
              "AllowedIPs = 0.0.0.0/0",
              "\n"
              )

    config_file = "/etc/wireguard/wg0.conf"
    os.system(f"sudo touch {config_file}")
    os.system(f"sudo chmod 666 {config_file}")
    with open(config_file, "w") as f:
        f.write("\n".join(config))
    os.system(f"sudo chmod 600 {config_file}")


if __name__ == "__main__":
    app()
