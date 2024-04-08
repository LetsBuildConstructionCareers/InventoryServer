from flask import Flask, jsonify
import sqlite3
import sys

app = Flask(__name__)
db_name = None

def convert_row_to_item(row):
    [barcode_id, picture_path] = row
    retval =  {'barcode_id': barcode_id, 'picture_path': picture_path}
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

if __name__ == '__main__':
    assert len(sys.argv) == 2
    db_name = sys.argv[1]
    app.run(host='0.0.0.0', debug=True)
