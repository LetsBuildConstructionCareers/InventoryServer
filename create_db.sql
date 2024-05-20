CREATE TABLE items (
    barcode_id STRING PRIMARY KEY,
    short_id STRING,
    name STRING,
    picture_path STRING,
    description TEXT
);

CREATE TABLE users (
    barcode_id STRING PRIMARY KEY,
    name STRING,
    company STRING,
    picture_path STRING,
    user_type STRING,
    description TEXT
);

CREATE TABLE user_checkins (
    user_id STRING,
    unix_time INTEGER
);

CREATE TABLE user_checkouts (
    user_id STRING,
    unix_time INTEGER
);

CREATE TABLE containers (
    container_id STRING,
    item_id STRING
);

CREATE TABLE vehicles (
    container_id STRING,
    item_id STRING
);

CREATE TABLE locations (
    container_id STRING,
    item_id STRING
);

CREATE TABLE toolshed_checkouts (
    checkout_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id STRING,
    user_id STRING,
    unix_time INTEGER,
    override_justification STRING
);

CREATE TABLE toolshed_checkins (
    checkin_id INTEGER PRIMARY KEY AUTOINCREMENT,
    checkout_id INTEGER,
    item_id STRING,
    user_id STRING,
    unix_time INTEGER,
    override_justification STRING,
    description TEXT
);

CREATE TABLE events (
    unix_time INTEGER,
    item_id STRING,
    container_id STRING,
    user_id STRING,
    device_id STRING,
    description TEXT
);

INSERT INTO items (barcode_id, picture_path) VALUES ("12-34", "picture");
INSERT INTO items (barcode_id, picture_path) VALUES ("9780913836316", "picture of book");
