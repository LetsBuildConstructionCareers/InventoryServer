from flask import Flask, jsonify, request, send_from_directory
import os.path
import sqlite3
import sys
import uuid

app = Flask(__name__)
db_name = None
picture_directory = None

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

if __name__ == '__main__':
    assert len(sys.argv) == 3
    db_name = sys.argv[1]
    picture_directory = sys.argv[2]
    app.run(host='0.0.0.0', debug=True)
