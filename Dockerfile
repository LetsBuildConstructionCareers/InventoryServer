# syntax=docker/dockerfile:1

FROM ubuntu:22.04
RUN apt update && apt install -y \
    sqlite3 \
    python3-pip
RUN pip3 install flask
RUN mkdir -p /app/pictures
ADD ./server.py /app
ADD ./create_db.sql /app
ADD ./execute_server.sh /app
RUN mkdir /app/certs
ADD ./certs/authorization.txt /app/certs
ADD ./certs/cert.pem /app/certs
ADD ./certs/key.pem /app/certs
RUN sqlite3 /app/items.db < /app/create_db.sql
CMD bash /app/execute_server.sh
