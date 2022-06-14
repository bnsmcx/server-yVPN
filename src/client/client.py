import typer

app = typer.Typer()


@app.command()
def create():
    """CREATE a new VPN endpoint"""
    pass


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
