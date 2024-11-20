from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB_NAME = "tracker.db"

def connect_db():
    return sqlite3.connect(DB_NAME)

@app.route('/announce', methods=['POST'])
def announce():
    data = request.json
    print(f"Received data: {data}")

    peer_ip = request.remote_addr
    peer_port = data.get("port")
    files = data.get("files", []) 

    if not peer_port:
        return jsonify({"error": "Port is required"}), 400

    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Register the peer (corrected query)
        cursor.execute(
            '''INSERT OR IGNORE INTO Peers (ip, port, last_active) VALUES (?, ?, ?)''', 
            (peer_ip, peer_port, datetime.now())
        )
        conn.commit()  # Commit after inserting the peer

        # Get peer ID
        cursor.execute('SELECT peer_id FROM Peers WHERE ip = ? AND port = ?', (peer_ip, peer_port))
        peer = cursor.fetchone()
        if peer:
            peer_id = peer[0]
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
    peer_ip = request.remote_addr
    peer_port = data.get("port")
    files = data.get("files", [])  # This now expects a list of files

    if not peer_port or not files:
        return jsonify({"error": "Port and files are required"}), 400

    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Get peer ID using IP and port
        print(f"Finding peer with IP: {peer_ip}, Port: {peer_port}")
        cursor.execute('SELECT peer_id FROM Peers WHERE ip = ? AND port = ?', (peer_ip, peer_port))
        peer = cursor.fetchone()
        if not peer:
            return jsonify({"error": "Peer not registered"}), 404

        peer_id = peer[0]
        print(f"Found Peer ID: {peer_id}")

        # Iterate over each file in the files list
        for file in files:
            file_hash = file.get("file_hash")
            pieces = file.get("pieces", [])

            if not file_hash or not pieces:
                return jsonify({"error": "File hash and pieces are required"}), 400

            # Check if the file exists in the Files table
            print(f"Checking file with hash: {file_hash}")
            cursor.execute('SELECT file_id FROM Files WHERE file_hash = ?', (file_hash,))
            result = cursor.fetchone()
            if not result:
                return jsonify({"error": f"File {file_hash} not found"}), 404

            file_id = result[0]
            print(f"Found File ID: {file_id}")

            # Register pieces associated with the file
            for piece_index in pieces:
                print(f"Inserting piece {piece_index} for file_id {file_id} and peer_id {peer_id}")
                cursor.execute(
                '''INSERT OR IGNORE INTO File_Pieces (file_id, peer_id, piece_index) VALUES (?, ?, ?)''',
                (file_id, peer_id, piece_index)
            )

        print("Committing changes to database...")
        conn.commit()
        print("Changes committed successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error during upload: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    return jsonify({"status": "files registered successfully"})



@app.route('/peers', methods=['GET'])
def get_peers():
    file_hash = request.args.get("file_hash")
    if not file_hash:
        return jsonify({"error": "file_hash is required"}), 400

    conn = connect_db()
    cursor = conn.cursor()

    # Get the file ID based on file_hash
    cursor.execute(
        '''
        SELECT file_id, file_name FROM Files WHERE file_hash = ?
        ''', (file_hash,)
    )
    result = cursor.fetchone()
    if not result:
        return jsonify({"error": "File not found"}), 404

    file_id, file_name = result

    # Get peers that have pieces of the file
    cursor.execute(
        '''
        SELECT Peers.ip, Peers.port, File_Pieces.piece_index
        FROM File_Pieces
        INNER JOIN Peers ON File_Pieces.peer_id = Peers.peer_id
        WHERE File_Pieces.file_id = ?
        ''', (file_id,)
    )
    peers = cursor.fetchall()
    print(f"Peers with pieces: {peers}") 

    conn.close()

    # Structure the response
    pieces = {}
    for ip, port, piece_index in peers:
        if piece_index not in pieces:
            pieces[piece_index] = []
        pieces[piece_index].append(f"{ip}:{port}")

    return jsonify({
        "file_name": file_name,  # Add the file name in the response
        "file_hash": file_hash,  # You can include the file hash too
        "pieces": pieces
    })



if __name__ == "__main__":
    app.run(port=5500)
