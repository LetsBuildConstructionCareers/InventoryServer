# syntax=docker/dockerfile:1

FROM ubuntu:22.04
RUN apt update && apt install -y \
    sqlite3 \
    python3-pip
RUN pip3 install flask
RUN mkdir -p /app/pictures
ADD ./server.py /app
ADD ./create_db.sql /app
RUN sqlite3 /app/items.db < /app/create_db.sql
CMD python3 /app/server.py /app/items.db /app/pictures
