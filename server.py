from flask import Flask, request, jsonify
import hashlib
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

db_config = {
    "host": "localhost",  
    "user": "root",       
    "password": "root",  
    "database": "file_sharing",  
    "port":3300,
}

def calculate_info_hash(file_name, file_size):
    data = f"{file_name}:{file_size}"
    return hashlib.sha256(data.encode()).hexdigest()

def execute_query(query, params=None):
    try:
        connection = mysql.connector.connect(**db_config)
        if(connection):
            print("connected")
        else:
            print("cannot connect")
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or ())
        if query.strip().lower().startswith("select"):
            result = cursor.fetchall()
        else:
            connection.commit()
            result = cursor.lastrowid
        cursor.close()
        connection.close()
        return result
    except Error as e:
        print(f"Error: {e}")
        return None

@app.route('/file/fetch', methods=['GET'])
def fetch_file():
    info_hash = request.args.get('info_hash')
    if not info_hash:
        return jsonify({
            "success": False,
            "message": "info_hash is required",
            "data": None
        }), 400

    query = "SELECT * FROM files WHERE info_hash = %s"
    result = execute_query(query, (info_hash,))

    if not result:
        return jsonify({
            "success": False,
            "message": "File not found",
            "data": None
        }), 404

    return jsonify({
        "success": True,
        "message": "File fetched successfully",
        "data": result[0]
    }), 200

@app.route('/file/publish', methods=['POST'])
def publish_file():
    try:
        data = request.json
        file_name = data.get("file_name")
        file_size = data.get("file_size")
        if not file_name or not file_size:
            return jsonify({
                "success": False,
                "message": "file_name and file_size are required",
                "data": None
            }), 400

        info_hash = calculate_info_hash(file_name, file_size)

        query = "SELECT * FROM files WHERE info_hash = %s"
        result = execute_query(query, (info_hash,))
        if result:
            return jsonify({
                "success": True,
                "message": "File already exists",
                "data": result[0]
            }), 200

        insert_query = "INSERT INTO files (info_hash, file_name, file_size) VALUES (%s, %s, %s)"
        execute_query(insert_query, (info_hash, file_name, file_size))

        return jsonify({
            "success": True,
            "message": "File published successfully",
            "data": {"info_hash": info_hash, "file_name": file_name, "file_size": file_size}
        }), 201
    except Exception as e:
        print(e)
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "data": None
        }), 500

@app.route('/file/peers/announce', methods=['POST'])
def announce_peer():
    try:
        data = request.json
        info_hash = data.get("info_hash")
        peer_address = data.get("peer_address")
        peer_port = data.get("peer_port")

        if not all([info_hash, peer_address, peer_port]):
            return jsonify({
                "success": False,
                "message": "info_hash, peer_address, and peer_port are required",
                "data": None
            }), 400

        query = "SELECT * FROM files WHERE info_hash = %s"
        result = execute_query(query, (info_hash,))
        if not result:
            return jsonify({
                "success": False,
                "message": "File not found",
                "data": None
            }), 404

        insert_query = "INSERT INTO peers (info_hash, peer_address, peer_port) VALUES (%s, %s, %s)"
        execute_query(insert_query, (info_hash, peer_address, peer_port))

        return jsonify({
            "success": True,
            "message": "Peer announced successfully",
            "data": {"info_hash": info_hash, "peer_address": peer_address, "peer_port": peer_port}
        }), 201
    except Exception as e:
        print(e)
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "data": None
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
