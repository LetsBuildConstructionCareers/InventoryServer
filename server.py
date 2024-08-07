from dataclasses import asdict, dataclass
from enum import Enum
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

@dataclass
class FullLocation:
    container_path: list[str]
    vehicle: Optional[str] = None
    location: Optional[str] = None

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

@dataclass
class InventoryEvent:
    id: int
    start_unix_time: int
    complete_unix_time: Optional[int] = None
    notes: Optional[str] = None

class InventoryStatus(Enum):
    GOOD = "GOOD"
    MISSING = "MISSING"
    WRONG_LOCATION = "WRONG_LOCATION"
    NEW_ITEM = "NEW_ITEM"
    DAMAGED = "DAMAGED"
    OTHER = "OTHER"

@dataclass
class InventoriedItem:
    inventory_id: int
    item_id: str
    status: str
    notes: Optional[str] = None

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

@app.route('/inventory/api/v1.0/registered-devices/<string:android_id>', methods=['GET'])
@check_auth_header
def get_registered_device_id(android_id):
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    res = cur.execute('SELECT barcode_id FROM registered_devices WHERE android_id = ?', (android_id,))
    maybe_barcode_id = res.fetchone()
    if maybe_barcode_id is not None and len(maybe_barcode_id) > 0:
        return jsonify(maybe_barcode_id[0])
    else:
        abort(404)

@app.route('/inventory/api/v1.0/unregistered-devices/', methods=['GET'])
@check_auth_header
def get_unregistered_devices():
    con = sqlite3.connect(db_name)
    con.row_factory = lambda cursor, row: str(*row)
    cur = con.cursor()
    android_ids = cur.execute('SELECT android_id FROM registered_devices WHERE barcode_id IS NULL')
    return jsonify(list(android_ids))

@app.route('/inventory/api/v1.0/unregistered-devices/<string:android_id>', methods=['PUT'])
@check_auth_header
def upload_device_id(android_id):
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    cur.execute('INSERT OR REPLACE INTO registered_devices (android_id) VALUES (:android_id)', {'android_id': android_id})
    con.commit()
    return '', 200

@app.route('/inventory/api/v1.0/registered-devices/<string:android_id>/<string:barcode_id>', methods=['POST'])
@check_auth_header
def register_device_id(android_id, barcode_id):
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    cur.execute('UPDATE registered_devices SET barcode_id = :barcode_id WHERE android_id = :android_id', {'android_id': android_id, 'barcode_id': barcode_id})
    con.commit()
    return '', 200

@app.route('/inventory/api/v1.0/items', methods=['GET'])
@check_auth_header
def get_items():
    con = sqlite3.connect(db_name)
    con.row_factory = row_to_item_factory
    cur = con.cursor()
    item_list = cur.execute('SELECT * FROM items;')
    return jsonify(list(item_list))

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

@app.route('/inventory/api/v1.0/full-location/<string:item_id>', methods=['GET'])
@check_auth_header
def get_full_location_of_item(item_id):
    container_path = get_full_container_path_of_item(item_id)
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    res = cur.execute('SELECT container_id FROM locations WHERE item_id = ?', (item_id,))
    container_ids = res.fetchone()
    if container_ids is not None and len(container_ids) > 0:
        return jsonify(FullLocation(container_path, location = container_ids[0]))
    res = cur.execute('SELECT container_id FROM vehicles WHERE item_id = ?', (item_id,))
    container_ids = res.fetchone()
    if container_ids is not None and len(container_ids) > 0:
        return jsonify(FullLocation(container_path, vehicle = container_ids[0]))
    return jsonify(FullLocation(container_path))

def get_full_container_path_of_item(item_id):
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    res = cur.execute('SELECT container_id FROM containers WHERE item_id = ?', (item_id,))
    container_ids = res.fetchone()
    if container_ids is not None and len(container_ids) > 0:
        return [container_ids[0]] + get_full_container_path_of_item(container_ids[0])
    else:
        return []

@app.route('/inventory/api/v1.0/item-parent/<string:item_id>', methods=['GET'])
@check_auth_header
def get_parent_of_item(item_id):
    full_location = get_full_container_path_of_item(item_id)
    if len(full_location) == 0:
        return jsonify('')
    container_id = full_location[0]
    return jsonify(container_id)

def does_item_exist(sql_cursor, barcode_id):
    res = sql_cursor.execute('SELECT count(*) FROM items WHERE barcode_id = ?', (barcode_id,))
    return res.fetchone()[0] > 0

@app.route('/inventory/api/v1.0/items-not-in-containers', methods=['GET'])
@check_auth_header
def get_all_items_not_in_containers():
    con = sqlite3.connect(db_name)
    con.row_factory = row_to_item_factory
    cur = con.cursor()
    items = cur.execute('SELECT items.* FROM items LEFT JOIN containers ON barcode_id = item_id WHERE container_id IS NULL')
    return jsonify(list(items))

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

@app.route('/inventory/api/v1.0/vehicles/<string:container_id>', methods=['GET'])
@check_auth_header
def get_items_in_vehicles(container_id):
    assert request.method == 'GET'
    con = sqlite3.connect(db_name)
    con.row_factory = lambda cursor, row: Item(*row)
    cur = con.cursor()
    items = cur.execute('SELECT items.* FROM items INNER JOIN vehicles ON items.barcode_id = vehicles.item_id WHERE container_id = ?', (container_id,))
    return jsonify(list(items))

@app.route('/inventory/api/v1.0/vehicles/<string:container_id>', methods=['POST'])
@check_auth_header
def add_items_to_vehicle(container_id):
    assert request.method == 'POST'
    item_ids = request.json
    assert len(item_ids) >= 1
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    assert does_item_exist(cur, container_id)
    for item_id in item_ids:
        assert does_item_exist(cur, item_id)
        cur.execute('INSERT OR REPLACE INTO vehicles (container_id, item_id) VALUES (:container_id, :item_id)', {'container_id': container_id, 'item_id': item_id})
    con.commit()
    return '', 200

@app.route('/inventory/api/v1.0/vehicles/<string:container_id>/<string:item_id>', methods=['DELETE'])
@check_auth_header
def remove_item_from_vehicle(container_id, item_id):
    assert request.method == 'DELETE'
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    cur.execute('DELETE FROM vehicles WHERE container_id = :container_id AND item_id = :item_id', {'container_id': container_id, 'item_id': item_id})
    con.commit()
    return '', 200

@app.route('/inventory/api/v1.0/locations/<string:container_id>', methods=['GET'])
@check_auth_header
def get_items_in_location(container_id):
    assert request.method == 'GET'
    con = sqlite3.connect(db_name)
    con.row_factory = lambda cursor, row: Item(*row)
    cur = con.cursor()
    items = cur.execute('SELECT items.* FROM items INNER JOIN locations ON items.barcode_id = locations.item_id WHERE container_id = ?', (container_id,))
    return jsonify(list(items))

@app.route('/inventory/api/v1.0/locations/<string:container_id>', methods=['POST'])
@check_auth_header
def add_items_to_location(container_id):
    assert request.method == 'POST'
    item_ids = request.json
    assert len(item_ids) >= 1
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    assert does_item_exist(cur, container_id)
    for item_id in item_ids:
        assert does_item_exist(cur, item_id)
        cur.execute('INSERT OR REPLACE INTO locations (container_id, item_id) VALUES (:container_id, :item_id)', {'container_id': container_id, 'item_id': item_id})
    con.commit()
    return '', 200

@app.route('/inventory/api/v1.0/locations/<string:container_id>/<string:item_id>', methods=['DELETE'])
@check_auth_header
def remove_item_from_location(container_id, item_id):
    assert request.method == 'DELETE'
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    cur.execute('DELETE FROM locations WHERE container_id = :container_id AND item_id = :item_id', {'container_id': container_id, 'item_id': item_id})
    con.commit()
    return '', 200

@app.route('/inventory/api/v1.0/inventory-events', methods=['GET'])
@check_auth_header
def get_inventory_events():
    con = sqlite3.connect(db_name)
    con.row_factory = lambda cursor, row: InventoryEvent(*row)
    cur = con.cursor()
    inventory_events = cur.execute('SELECT * FROM inventory_events')
    return jsonify(list(inventory_events))

@app.route('/inventory/api/v1.0/inventory-events', methods=['POST'])
@check_auth_header
def create_new_inventory_event():
    con = sqlite3.connect(db_name)
    con.row_factory = lambda cursor, row: InventoryEvent(*row)
    cur = con.cursor()
    current_time = int(time.time())
    cur.execute('INSERT INTO inventory_events (start_unix_time) VALUES (:current_time)', {'current_time': current_time})
    con.commit()
    res = cur.execute('SELECT * FROM inventory_events WHERE start_unix_time = :current_time', {'current_time': current_time})
    id = res.fetchone()
    print(id)
    return jsonify(id)

@app.route('/inventory/api/v1.0/inventory-events', methods=['PATCH'])
@check_auth_header
def update_inventory_event_complete_time_and_notes():
    inventory_event = InventoryEvent(**request.json)
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    cur.execute('UPDATE inventory_events SET complete_unix_time = :complete_unix_time, notes = :notes WHERE id = :id',
            {'id': inventory_event.id, 'complete_unix_time': inventory_event.complete_unix_time, 'notes': inventory_event.notes})
    con.commit()
    return '', 200

@app.route('/inventory/api/v1.0/inventoried-items-not-in-containers/<int:inventory_id>', methods=['GET'])
@check_auth_header
def get_all_inventoried_items_not_in_containers(inventory_id):
    con = sqlite3.connect(db_name)
    con.row_factory = lambda cursor, row: InventoriedItem(*row)
    cur = con.cursor()
    inventoried_items = cur.execute('SELECT inventoried_items.* FROM inventoried_items LEFT JOIN containers ON inventoried_items.item_id = containers.item_id WHERE container_id IS NULL AND inventory_id = :inventory_id', {'inventory_id': inventory_id})
    return jsonify(list(inventoried_items))

@app.route('/inventory/api/v1.0/inventoried-items-in-container/<int:inventory_id>/<string:container_id>', methods=['GET'])
@check_auth_header
def get_all_inventoried_items_in_container(inventory_id, container_id):
    assert request.method == 'GET'
    con = sqlite3.connect(db_name)
    con.row_factory = lambda cursor, row: InventoriedItem(*row)
    cur = con.cursor()
    items = cur.execute('SELECT inventoried_items.* FROM inventoried_items INNER JOIN containers ON inventoried_items.item_id = containers.item_id WHERE container_id = :container_id AND inventory_id = :inventory_id', {'container_id': container_id, 'inventory_id': inventory_id})
    return jsonify(list(items))

@app.route('/inventory/api/v1.0/inventoried-items-uninventoried/<int:inventory_id>', methods=['GET'])
@check_auth_header
def get_all_uninventoried_items(inventory_id):
    con = sqlite3.connect(db_name)
    con.row_factory = lambda cursor, row: Item(*row)
    cur = con.cursor()
    items = cur.execute(
    'SELECT items.* FROM items INNER JOIN (SELECT barcode_id AS id FROM items EXCEPT SELECT item_id AS id FROM inventoried_items WHERE inventory_id = :inventory_id) ON barcode_id = id',
    {'inventory_id': inventory_id})
    return jsonify(list(items))

@app.route('/inventory/api/v1.0/inventoried-items-not-good/<int:inventory_id>', methods=['GET'])
@check_auth_header
def get_all_not_good_inventoried_items(inventory_id):
    con = sqlite3.connect(db_name)
    con.row_factory = lambda cursor, row: InventoriedItem(*row)
    cur = con.cursor()
    inventoried_items = cur.execute('SELECT * FROM inventoried_items WHERE status != :good_inventory_status AND inventory_id = :inventory_id',
            {'good_inventory_status': InventoryStatus.GOOD.value, 'inventory_id': inventory_id})
    return jsonify(list(inventoried_items))

@app.route('/inventory/api/v1.0/inventoried-items/<int:inventory_id>/<string:item_id>', methods=['GET'])
@check_auth_header
def get_inventoried_item(inventory_id, item_id):
    con = sqlite3.connect(db_name)
    con.row_factory = lambda cursor, row: InventoriedItem(*row)
    cur = con.cursor()
    inventoried_item = cur.execute('SELECT * FROM inventoried_items WHERE inventory_id = :inventory_id AND item_id = :item_id', {'inventory_id': inventory_id, 'item_id': item_id})
    inventoried_item = inventoried_item.fetchone()
    return jsonify(inventoried_item)

@app.route('/inventory/api/v1.0/inventoried-items', methods=['POST'])
@check_auth_header
def add_inventoried_item():
    inventoried_item = InventoriedItem(**request.json)
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    cur.execute('INSERT OR REPLACE INTO inventoried_items (inventory_id, item_id, status, notes) VALUES (:inventory_id, :item_id, :status, :notes)', asdict(inventoried_item))
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
    res = cur.execute('SELECT toolshed_checkouts.* FROM toolshed_checkouts LEFT JOIN toolshed_checkins ON toolshed_checkouts.checkout_id = toolshed_checkins.checkout_id WHERE toolshed_checkins.checkout_id IS NULL AND toolshed_checkouts.item_id = :item_id AND toolshed_checkouts.checkout_id = (SELECT checkout_id FROM toolshed_checkouts WHERE item_id = :item_id ORDER BY unix_time DESC LIMIT 1)', {'item_id': barcode_id})
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

@app.route('/inventory/api/v1.0/users-checkedin/', methods=['GET'])
def get_checked_in_users():
    con = sqlite3.connect(db_name)
    con.row_factory = lambda cursor, row: User(*row)
    cur = con.cursor()
    users = cur.execute('SELECT users.* FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY unix_time DESC) AS row_num FROM (SELECT "checkin" AS type, * FROM user_checkins UNION SELECT "checkout" AS type, * FROM user_checkouts)) INNER JOIN users ON user_id = barcode_id WHERE row_num == 1 AND type == "checkin"')
    users = list(users)
    return jsonify(users)

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
