CREATE TABLE items (
    barcode_id STRING PRIMARY KEY,
    short_id STRING,
    name STRING,
    picture_path STRING,
    description TEXT
);

CREATE TABLE registered_devices (
    android_id STRING PRIMARY KEY,
    barcode_id STRING
);

CREATE TABLE users (
    barcode_id STRING PRIMARY KEY,
    name STRING,
    company STRING,
    picture_path STRING,
    user_type STRING,
    description TEXT,
    initial_checkin_info TEXT
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

CREATE TABLE inventory_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_unix_time INTEGER,
    complete_unix_time INTEGER,
    notes STRING
);

CREATE TABLE inventoried_items (
    inventory_id INTEGER,
    item_id STRING,
    status STRING,
    notes STRING,
    UNIQUE(inventory_id, item_id) ON CONFLICT REPLACE
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
