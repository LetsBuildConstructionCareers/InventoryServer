# syntax=docker/dockerfile:1

FROM ubuntu:22.04
COPY . /app
RUN apt update && apt install -y \
    sqlite3
RUN pip3 install flask
#RUN make /app
RUN sqlite3 items.db </app/create_db.sql
CMD bash
#CMD python /app/app.py
