# InventoryServer

The server for https://github.com/LetsBuildConstructionCareers/InventoryScanner.
Primarily provides a fairly thin set of REST endpoints for a SQL database.

## Building

The intended way to build and deploy is with Docker:

```bash
docker build --tag='test_inventory_server
docker run -i -p 5000:5000 'test_inventory_server'
```

**NB**: Make a note of the IP address of the server and make sure it matches the
IP address of the InventoryScanner.

## Building/Deploying for Development

It may be more convenient to run the server in the development environment:

```bash
sudo apt update && apt install -y \
    sqlite3 \
    python3-pip
pip3 install flask
sqlite3 items.db <create_db.sql
mkdir pictures
python3 server.py items.db pictures
```
