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
    "port": 3300,
}
def calculate_info_hash(file_name, file_size):
    # Combine the file name and size into a single string
    data = f"{file_name}:{file_size}"
    
    # Create a SHA-256 hash from the string
    info_hash = hashlib.sha256(data.encode()).hexdigest()
    
    return info_hash
def execute_query(query, params=None):
    try:
        connection = mysql.connector.connect(**db_config)
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

@app.route('/file/publish', methods=['POST'])
def publish_file():
    try:
        data = request.json
        file_name = data.get("file_name")
        file_size = data.get("file_size")
        peer_address = data.get("peer_address")
        peer_port = data.get("peer_port")

        if not all([file_name, file_size, peer_address, peer_port]):
            return jsonify({
                "success": False,
                "message": "file_name, file_size, peer_address, and peer_port are required",
                "data": None
            }), 400

        # Calculate info_hash for the file
        info_hash = calculate_info_hash(file_name, file_size)

        # Check if the file already exists
        query = "SELECT * FROM files WHERE info_hash = %s"
        result = execute_query(query, (info_hash,))
        if result:
            return jsonify({
                "success": True,
                "message": "File already exists",
                "data": result[0]
            }), 200

        # Insert file into files table
        insert_file_query = "INSERT INTO files (info_hash, file_name, file_size) VALUES (%s, %s, %s)"
        execute_query(insert_file_query, (info_hash, file_name, file_size))

        # Add the publisher as the first peer for the file
        insert_peer_query = """
            INSERT INTO peers (info_hash, peer_address, peer_port)
            VALUES (%s, %s, %s)
        """
        execute_query(insert_peer_query, (info_hash, peer_address, peer_port))

        return jsonify({
            "success": True,
            "message": "File published successfully",
            "data": {
                "info_hash": info_hash,
                "file_name": file_name,
                "file_size": file_size,
                "publisher": {"peer_address": peer_address, "peer_port": peer_port}
            }
        }), 201

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "data": None
        }), 500
@app.route('/file/peers', methods=['GET'])
def get_peers():
    info_hash = request.args.get("info_hash")
    if not info_hash:
        return jsonify({"success": False, "message": "info_hash is required"}), 400

    try:
        # Query the database for peers associated with the given info_hash
        peer_query = """
            SELECT peer_address, peer_port 
            FROM peers 
            WHERE info_hash = %s
        """
        peers = execute_query(peer_query, (info_hash,))
        if not peers:
            return jsonify({"success": False, "message": "No peers found for the provided info_hash"}), 404

        return jsonify({"success": True, "peers": peers}), 200

    except Exception as e:
        print(f"Error: {e}")
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
        chunks = data.get("chunks")

        if not all([info_hash, peer_address, peer_port, chunks]):
            return jsonify({
                "success": False,
                "message": "info_hash, peer_address, peer_port, and chunks are required",
                "data": None
            }), 400

        # Check if the file exists
        query = "SELECT * FROM files WHERE info_hash = %s"
        file_result = execute_query(query, (info_hash,))
        if not file_result:
            return jsonify({
                "success": False,
                "message": "File not found",
                "data": None
            }), 404

        # Insert or find the peer
        peer_query = """
        INSERT INTO peers (info_hash, peer_address, peer_port)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)
        """
        peer_id = execute_query(peer_query, (info_hash, peer_address, peer_port))

        # Store the chunks
        for chunk_index in chunks:
            chunk_query = """
            INSERT IGNORE INTO chunks (peer_id, chunk_index)
            VALUES (%s, %s)
            """
            execute_query(chunk_query, (peer_id, chunk_index))

        return jsonify({
            "success": True,
            "message": "Peer and chunks announced successfully",
            "data": {"info_hash": info_hash, "peer_address": peer_address, "peer_port": peer_port, "chunks": chunks}
        }), 201

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "data": None
        }), 500

@app.route('/file/fetch', methods=['GET'])
def fetch_file():
    info_hash = request.args.get("info_hash")
    if not info_hash:
        return jsonify({"success": False, "message": "info_hash is required"}), 400

    query = "SELECT * FROM files WHERE info_hash = %s"
    file_data = execute_query(query, (info_hash,))
    if not file_data:
        return jsonify({"success": False, "message": "File not found"}), 404

    peer_query = """
        SELECT p.peer_address, p.peer_port, c.chunk_index 
        FROM peers p 
        JOIN chunks c ON p.id = c.peer_id 
        WHERE p.info_hash = %s
    """
    peers = execute_query(peer_query, (info_hash,))
    return jsonify({"success": True, "file": file_data[0], "peers": peers}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
