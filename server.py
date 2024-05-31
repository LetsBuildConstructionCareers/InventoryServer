from dataclasses import asdict, dataclass
from flask import Flask, jsonify, request, send_from_directory, abort
from functools import wraps
from typing import Optional
import os.path
import time
import sqlite3
import sys
import uuid

app = Flask(__name__)
db_name = None
picture_directory = None
auth_value = None

@dataclass
class Item:
    barcode_id: str
    short_id: str
    name: str
    picture_path: str
    description: str

def adapt_item(item):
    return f'{item.barcode_id};{item.short_id};{item.name};{item.picture_path};{item.description}'

def convert_item(item):
    barcode_id, short_id, name, picture_path, description = list(map(str, s.split(b";")))
    return Item(barcode_id, short_id, name, picture_path, description)

sqlite3.register_adapter(Item, adapt_item)
sqlite3.register_converter("item", convert_item)

@dataclass
class User:
    barcode_id: str
    name: str
    company: str
    picture_path: str
    user_type: str
    description: str
    initial_checkin_info: str

@dataclass
class ToolshedCheckout:
    checkout_id: Optional[int] = None
    item_id: Optional[str] = None
    user_id: Optional[str] = None
    unix_time: Optional[int] = None
    override_justification: Optional[str] = None

@dataclass
class ToolshedCheckin:
    checkin_id: Optional[int] = None
    checkout_id: Optional[int] = None
    item_id: Optional[str] = None
    user_id: Optional[str] = None
    unix_time: Optional[int] = None
    override_justification: Optional[str] = None
    description: Optional[str] = None

def adapt_user(user):
    return f"{user.barcode_id};{user.name};{user.company};{user.description}"

def convert_user(s):
    barcode_id, name, company, picture_path, description = list(map(str, s.split(b";")))
    return User(barcode_id, name, company, picture_path, description)

sqlite3.register_adapter(User, adapt_user)
sqlite3.register_converter("user", convert_user)

def row_to_item_factory(cursor, row):
    return Item(*row)

def do_check_auth_header(request):
    print('Expected Auth: ' + auth_value)
    print(str(request))
    sys.stdout.flush()
    if (request.headers.get('Authorization') == auth_value):
        return
    else:
        abort(401)

def check_auth_header(func):
    @wraps(func)
    def decorated_func(*args, **kwargs):
        do_check_auth_header(request)
        return func(*args, **kwargs)
    return decorated_func

@app.route('/inventory/api/v1.0/items', methods=['GET'])
@check_auth_header
def get_items():
    con = sqlite3.connect(db_name)
    con.row_factory = row_to_item_factory
    cur = con.cursor()
    item_list = cur.execute('SELECT * FROM items;')
    return jsonify({'items': item_list})

@app.route('/inventory/api/v1.0/items/<string:barcode_id>', methods=['GET'])
@check_auth_header
def get_item(barcode_id):
    print(barcode_id)
    con = sqlite3.connect(db_name)
    con.row_factory = row_to_item_factory
    cur = con.cursor()
    res = cur.execute('SELECT * FROM items WHERE barcode_id = ?', (barcode_id,))
    item = res.fetchone()
    print(item)
    retval = jsonify(item)
    print(retval)
    return retval

@app.route('/inventory/api/v1.0/item-picture/<string:barcode_id>', methods=['GET'])
@check_auth_header
def get_item_pictures(barcode_id):
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    res = cur.execute('SELECT picture_path FROM items WHERE barcode_id = ?', (barcode_id,))
    [picture_path] = res.fetchone()
    return send_from_directory(picture_directory, picture_path)

@app.route('/inventory/api/v1.0/items/<string:barcode_id>', methods=['POST'])
@check_auth_header
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

def get_full_location_of_item(item_id):
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    res = cur.execute('SELECT container_id FROM containers WHERE item_id = ?', (item_id,))
    container_ids = res.fetchone()
    if container_ids is not None and len(container_ids) > 0:
        return [container_ids[0]] + get_full_location_of_item(container_ids[0])
    else:
        return []

@app.route('/inventory/api/v1.0/item-parent/<string:item_id>', methods=['GET'])
@check_auth_header
def get_parent_of_item(item_id):
    full_location = get_full_location_of_item(item_id)
    if len(full_location) == 0:
        return jsonify('')
    container_id = full_location[0]
    return jsonify(container_id)

def does_item_exist(sql_cursor, barcode_id):
    res = sql_cursor.execute('SELECT count(*) FROM items WHERE barcode_id = ?', (barcode_id,))
    return res.fetchone()[0] > 0

@app.route('/inventory/api/v1.0/containers/<string:container_id>', methods=['GET'])
@check_auth_header
def get_items_in_container(container_id):
    assert request.method == 'GET'
    con = sqlite3.connect(db_name)
    con.row_factory = lambda cursor, row: Item(*row)
    cur = con.cursor()
    items = cur.execute('SELECT items.* FROM items INNER JOIN containers ON items.barcode_id = containers.item_id WHERE container_id = ?', (container_id,))
    return jsonify(list(items))

@app.route('/inventory/api/v1.0/containers/<string:container_id>', methods=['POST'])
@check_auth_header
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

@app.route('/inventory/api/v1.0/containers/<string:container_id>/<string:item_id>', methods=['DELETE'])
@check_auth_header
def remove_item_from_container(container_id, item_id):
    assert request.method == 'DELETE'
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    cur.execute('DELETE FROM containers WHERE container_id = :container_id AND item_id = :item_id', {'container_id': container_id, 'item_id': item_id})
    con.commit()
    return '', 200

@app.route('/inventory/api/v1.0/toolshed-checkout', methods=['POST'])
@check_auth_header
def checkout_from_toolshed():
    assert request.method == 'POST'
    toolshed_checkout = request.json
    toolshed_checkout['unix_time'] = int(time.time())
    toolshed_checkout = ToolshedCheckout(**toolshed_checkout)
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    cur.execute('INSERT OR REPLACE INTO toolshed_checkouts (item_id, user_id, unix_time) VALUES (:item_id, :user_id, :unix_time)',
            {'item_id': toolshed_checkout.item_id, 'user_id': toolshed_checkout.user_id, 'unix_time': toolshed_checkout.unix_time})
    con.commit()
    return '', 200

@app.route('/inventory/api/v1.0/toolshed-checkout/<string:barcode_id>/last-outstanding', methods=['GET'])
@check_auth_header
def get_last_outstanding_checkout(barcode_id):
    con = sqlite3.connect(db_name)
    con.row_factory = lambda cursor, row: ToolshedCheckout(*row)
    cur = con.cursor()
    res = cur.execute('SELECT toolshed_checkouts.* FROM toolshed_checkouts LEFT JOIN toolshed_checkins ON toolshed_checkouts.checkout_id = toolshed_checkins.checkout_id WHERE toolshed_checkins.checkout_id IS NULL AND toolshed_checkouts.item_id = ? AND toolshed_checkouts.checkout_id = (SELECT checkout_id FROM toolshed_checkouts ORDER BY unix_time DESC LIMIT 1)', (barcode_id,))
    outstanding_checkout = res.fetchone()
    print(outstanding_checkout)
    return jsonify(outstanding_checkout)

@app.route('/inventory/api/v1.0/toolshed-checkin', methods=['POST'])
@check_auth_header
def checkin_to_toolshed():
    assert request.method == 'POST'
    toolshed_checkin = request.json
    print(toolshed_checkin)
    toolshed_checkin['unix_time'] = int(time.time())
    toolshed_checkin = ToolshedCheckin(**toolshed_checkin)
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    cur.execute('INSERT OR REPLACE INTO toolshed_checkins (checkout_id, item_id, user_id, unix_time, override_justification, description) VALUES (:checkout_id, :item_id, :user_id, :unix_time, :override_justification, :description)', asdict(toolshed_checkin))
    con.commit()
    return '', 200

@app.route('/inventory/api/v1.0/users/<string:user_id>/toolshed-checkout-outstanding', methods=['GET'])
@check_auth_header
def get_items_checked_out_by_user(user_id):
    con = sqlite3.connect(db_name)
    con.row_factory = row_to_item_factory
    cur = con.cursor()
    items = cur.execute('SELECT items.* FROM toolshed_checkouts \
            LEFT JOIN toolshed_checkins ON toolshed_checkouts.checkout_id = toolshed_checkins.checkout_id \
            INNER JOIN items ON toolshed_checkouts.item_id = items.barcode_id \
            WHERE toolshed_checkins.checkout_id IS NULL AND toolshed_checkouts.user_id = ?', (user_id,))
    return jsonify(list(items))

@app.route('/inventory/api/v1.0/users-toolshed-checkout-outstanding', methods=['GET'])
@check_auth_header
def get_users_with_outstanding_toolshed_checkouts():
    con = sqlite3.connect(db_name)
    con.row_factory = lambda cursor, row: User(*row)
    cur = con.cursor()
    users = cur.execute('SELECT DISTINCT users.* FROM toolshed_checkouts \
            LEFT JOIN toolshed_checkins ON toolshed_checkouts.checkout_id = toolshed_checkins.checkout_id \
            INNER JOIN users ON toolshed_checkouts.user_id = users.barcode_id \
            WHERE toolshed_checkins.checkout_id IS NULL')
    return jsonify(list(users))

@app.route('/inventory/api/v1.0/users/<string:barcode_id>', methods=['GET'])
@check_auth_header
def get_user(barcode_id):
    con = sqlite3.connect(db_name)
    con.row_factory = lambda cursor, row: User(*row)
    cur = con.cursor()
    [user] = cur.execute('SELECT * FROM users WHERE barcode_id = ?', (barcode_id,))
    print(user)
    retval = jsonify(user)
    print(retval)
    return retval

@app.route('/inventory/api/v1.0/user-picture/<string:user_id>', methods=['GET'])
@check_auth_header
def get_user_picture(user_id):
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    res = cur.execute('SELECT picture_path FROM users WHERE barcode_id = ?', (user_id,))
    [picture_path] = res.fetchone()
    return send_from_directory(picture_directory, picture_path)

@app.route('/inventory/api/v1.0/user-picture/<string:user_id>', methods=['POST'])
@check_auth_header
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

@app.route('/inventory/api/v1.0/user-checkin/<string:user_id>', methods=['POST'])
@check_auth_header
def checkin_user(user_id):
    assert request.method == 'POST'
    unix_time = int(time.time())
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    cur.execute('INSERT OR REPLACE INTO user_checkins (user_id, unix_time) VALUES (:user_id, :unix_time)', {'user_id': user_id, 'unix_time': unix_time})
    con.commit()
    return '', 200

@app.route('/inventory/api/v1.0/user-checkout/<string:user_id>', methods=['POST'])
@check_auth_header
def checkout_user(user_id):
    assert request.method == 'POST'
    unix_time = int(time.time())
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    cur.execute('INSERT OR REPLACE INTO user_checkouts (user_id, unix_time) VALUES (:user_id, :unix_time)', {'user_id': user_id, 'unix_time': unix_time})
    con.commit()
    return '', 200

@app.route('/inventory/api/v1.0/users/', methods=['POST'])
@check_auth_header
def create_user_without_picture():
    assert request.method == 'POST'
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    user = request.json
    user = User(**user)
    cur.execute('INSERT OR REPLACE INTO users (barcode_id, name, company, user_type, description, initial_checkin_info) VALUES (:barcode_id, :name, :company, :user_type, :description, :initial_checkin_info)', asdict(user))
    con.commit()
    return '', 200

if __name__ == '__main__':
    assert len(sys.argv) == 6
    db_name = sys.argv[1]
    picture_directory = sys.argv[2]
    auth_value = open(sys.argv[3], 'r').read().strip()
    cert=sys.argv[4]
    key=sys.argv[5]
    app.run(host='0.0.0.0', debug=True)
    #app.run(host='0.0.0.0', debug=True, ssl_context=(cert, key))
