if [[ -a /storage ]]; then
    if [[ ! -a /storage/items.db ]]; then
        cp /app/items.db /storage/
    fi
    if [[ ! -a /storage/pictures ]]; then
        mkdir /storage/pictures
    fi
    python3 /app/server.py /storage/items.db /storage/pictures /app/certs/authorization.txt /app/certs/cert.pem /app/certs/key.pem
else
    python3 /app/server.py /app/items.db /app/pictures /app/certs/authorization.txt /app/certs/cert.pem /app/certs/key.pem
fi
