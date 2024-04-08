from flask import Flask, jsonify
import sqlite3
import sys

app = Flask(__name__)
db_name = None

@app.route('/inventory/api/v1.0/items', methods=['GET'])
def get_items():
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    res = cur.execute('SELECT * FROM items;')
    return jsonify({'items': res.fetchall()})

@app.route('/inventory/api/v1.0/items/<string:barcode_id>', methods=['GET'])
def get_item(barcode_id):
    print(barcode_id)
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    res = cur.execute('SELECT * FROM items WHERE barcode_id = ?', (barcode_id,))
    return jsonify({'item': res.fetchone()})

if __name__ == '__main__':
    assert len(sys.argv) == 2
    db_name = sys.argv[1]
    app.run(debug=True)
