import typer
import os

app = typer.Typer()


@app.command()
def create():
    """CREATE a new VPN endpoint"""
    # TODO: implement Digital Ocean API creation of droplet

    refresh_client_keys()

    # give server client's public key and IP

    # activate client on server

    # get server public key

    # build client config
    pass


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


def wireguard_installed():
    return True


if __name__ == "__main__":
    if wireguard_installed():
        app()
    else:
        typer.echo("[!] error: wireguard not found, install from apt and retry")
