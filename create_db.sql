CREATE TABLE items (
    barcode_id STRING PRIMARY KEY,
    picture_path STRING
);

INSERT INTO items (barcode_id, picture_path) VALUES ("12-34", "picture");
INSERT INTO items (barcode_id, picture_path) VALUES ("9780913836316", "picture of book");
