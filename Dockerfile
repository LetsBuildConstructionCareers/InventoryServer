# syntax=docker/dockerfile:1

FROM ubuntu:22.04
RUN apt update && apt install -y \
    sqlite3 \
    python3-pip
RUN pip3 install flask
COPY . /app
#RUN make /app
RUN sqlite3 items.db </app/create_db.sql
CMD python3 /app/server.py items.db
