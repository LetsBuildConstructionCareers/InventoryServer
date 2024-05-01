from dataclasses import dataclass
from flask import Flask, jsonify, request, send_from_directory
import os.path
import sqlite3
import sys
import uuid

app = Flask(__name__)
db_name = None
picture_directory = None

@dataclass
class User:
    barcode_id: str
    name: str
    company: str
    picture_path: str
    description: str

def adapt_user(user):
    return f"{user.barcode_id};{user.name};{user.company};{user.description}"

def convert_user(s):
    barcode_id, name, company, picture_path, description = list(map(str, s.split(b";")))
    return User(barcode_id, name, company, picture_path, description)

sqlite3.register_adapter(User, adapt_user)
sqlite3.register_converter("user", convert_user)

def convert_row_to_item(row):
    [barcode_id, name, picture_path] = row
    retval =  {'barcode_id': barcode_id, 'name': name}
    print(retval)
    return retval

@app.route('/inventory/api/v1.0/items', methods=['GET'])
def get_items():
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    res = cur.execute('SELECT * FROM items;')
    item_list = [convert_row_to_item(row) for row in res]
    return jsonify({'items': item_list})

@app.route('/inventory/api/v1.0/items/<string:barcode_id>', methods=['GET'])
def get_item(barcode_id):
    print(barcode_id)
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    res = cur.execute('SELECT * FROM items WHERE barcode_id = ?', (barcode_id,))
    retval = jsonify(convert_row_to_item(res.fetchone()))
    print(retval)
    return retval

@app.route('/inventory/api/v1.0/item-picture/<string:barcode_id>', methods=['GET'])
def get_item_pictures(barcode_id):
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    res = cur.execute('SELECT picture_path FROM items WHERE barcode_id = ?', (barcode_id,))
    [picture_path] = res.fetchone()
    return send_from_directory(picture_directory, picture_path)

@app.route('/inventory/api/v1.0/items/<string:barcode_id>', methods=['POST'])
def upload_item(barcode_id):
    assert request.method == 'POST'
    unique_filename = str(uuid.uuid4())
    file = request.files['picture']
    file.save(os.path.join(picture_directory, unique_filename))
    name = request.form['name']
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    cur.execute('INSERT OR REPLACE INTO items (barcode_id, name, picture_path) VALUES (:barcode_id, :name, :picture_path)', {'barcode_id': barcode_id, 'name': name, 'picture_path': unique_filename})
    con.commit()
    return '', 200

def does_item_exist(sql_cursor, barcode_id):
    res = sql_cursor.execute('SELECT count(*) FROM items WHERE barcode_id = ?', (barcode_id,))
    return res.fetchone()[0] > 0

@app.route('/inventory/api/v1.0/containers/<string:container_id>', methods=['POST'])
def add_items_to_container(container_id):
    assert request.method == 'POST'
    item_ids = request.json
    assert len(item_ids) >= 1
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    assert does_item_exist(cur, container_id)
    for item_id in item_ids:
        assert does_item_exist(cur, item_id)
        cur.execute('INSERT OR REPLACE INTO containers (container_id, item_id) VALUES (:container_id, :item_id)', {'container_id': container_id, 'item_id': item_id})
    con.commit()
    return '', 200

@app.route('/inventory/api/v1.0/users/<string:barcode_id>', methods=['GET'])
def get_user(barcode_id):
    con = sqlite3.connect(db_name)
    con.row_factory = lambda cursor, row: User(*row)
    cur = con.cursor()
    [user] = cur.execute('SELECT * FROM users WHERE barcode_id = ?', (barcode_id,))
    print(user)
    retval = jsonify(user)
    print(retval)
    return retval

@app.route('/inventory/api/v1.0/user-picture/<string:user_id>', methods=['POST'])
def uploadUserPicture(user_id):
    assert request.method == 'POST'
    unique_filename = str(uuid.uuid4())
    file = request.files['picture']
    file.save(os.path.join(picture_directory, unique_filename))
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    cur.execute('UPDATE users SET picture_path = :picture_path WHERE barcode_id = :barcode_id', {'barcode_id': user_id, 'picture_path': unique_filename})
    con.commit()
    return '', 200

if __name__ == '__main__':
    assert len(sys.argv) == 3
    db_name = sys.argv[1]
    picture_directory = sys.argv[2]
    app.run(host='0.0.0.0', debug=True)
