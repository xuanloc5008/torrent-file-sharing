from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error
from datetime import datetime

app = Flask(__name__)

DB_CONFIG = {
    'host': 'truntrun.ddns.net',
    'user': 'tuanemtramtinh',
    'password': 'TuanAnh_0908',
    'database': 'assignment',
    'port': 3306  
}


def connect_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        raise

@app.route('/announce', methods=['POST'])
def announce():
    data = request.json
    print(f"Received data: {data}")

    peer_ip = data.get("ip")
    peer_port = data.get("port")
    files = data.get("files", []) 

    if not peer_port:
        return jsonify({"error": "Port is required"}), 400

    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    try:
        # Register the peer
        cursor.execute(
            '''INSERT IGNORE INTO Peers (ip, port, last_active) VALUES (%s, %s, %s)''', 
            (peer_ip, peer_port, datetime.now())
        )
        conn.commit()

        # Get peer ID
        cursor.execute('SELECT peer_id FROM Peers WHERE ip = %s AND port = %s', (peer_ip, peer_port))
        peer = cursor.fetchone()
        if peer:
            peer_id = peer['peer_id']
        else:
            return jsonify({"error": "Peer registration failed"}), 500

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    return jsonify({"status": "success"})

@app.route('/upload', methods=['POST'])
def upload():
    data = request.json
    peer_ip = "192.168.83.48"
    peer_port = data.get("port")
    files = data.get("files", []) 

    if not peer_port or not files:
        return jsonify({"error": "Port and files are required"}), 400

    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get peer ID using IP and port
        cursor.execute('SELECT peer_id FROM Peers WHERE ip = %s AND port = %s', (peer_ip, peer_port))
        peer = cursor.fetchone()
        if not peer:
            return jsonify({"error": "Peer not registered"}), 404

        peer_id = peer['peer_id']

        # Iterate over each file in the files list
        for file in files:
            file_hash = file.get("file_hash")
            pieces = file.get("pieces", [])

            if not file_hash or not pieces:
                return jsonify({"error": "File hash and pieces are required"}), 400

            # Check if the file exists in the Files table
            cursor.execute('SELECT file_id FROM Files WHERE file_hash = %s', (file_hash,))
            result = cursor.fetchone()
            if not result:
                return jsonify({"error": f"File {file_hash} not found"}), 404

            file_id = result['file_id']

            # Register pieces associated with the file
            for piece_index in pieces:
                cursor.execute(
                    '''INSERT IGNORE INTO File_Pieces (file_id, peer_id, piece_index) VALUES (%s, %s, %s)''',
                    (file_id, peer_id, piece_index)
                )

        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    return jsonify({"status": "files registered successfully"})

@app.route('/files', methods=['GET'])
def get_files():
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT file_hash, file_name, total_pieces FROM Files")
    files = cursor.fetchall()

    conn.close()
    return jsonify(files)

@app.route('/peers', methods=['GET'])
def get_peers():
    file_hash = request.args.get("file_hash")
    if not file_hash:
        return jsonify({"error": "file_hash is required"}), 400

    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    # Get the file ID based on file_hash
    cursor.execute('SELECT file_id, file_name FROM Files WHERE file_hash = %s', (file_hash,))
    result = cursor.fetchone()
    if not result:
        return jsonify({"error": "File not found"}), 404

    file_id = result['file_id']
    file_name = result['file_name']

    # Get peers that have pieces of the file
    cursor.execute(
        '''
        SELECT Peers.ip, Peers.port, File_Pieces.piece_index
        FROM File_Pieces
        INNER JOIN Peers ON File_Pieces.peer_id = Peers.peer_id
        WHERE File_Pieces.file_id = %s
        ''', (file_id,)
    )
    peers = cursor.fetchall()

    conn.close()

    # Structure the response
    pieces = {}
    for peer in peers:
        ip_port = f"{peer['ip']}:{peer['port']}"
        pieces.setdefault(peer['piece_index'], []).append(ip_port)

    return jsonify({
        "file_name": file_name,
        "file_hash": file_hash,
        "pieces": pieces
    })

if __name__ == "__main__":
    app.run(port=5500)
