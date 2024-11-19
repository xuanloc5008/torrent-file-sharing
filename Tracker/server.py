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
    peer_ip = request.remote_addr
    peer_port = data.get("port")
    files = data.get("files")  

    if not peer_port or not files:
        return jsonify({"error": "Invalid data"}), 400

    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Register peer (corrected query)
        cursor.execute(
            '''INSERT OR IGNORE INTO Peers (ip, port, last_active) VALUES (?, ?, ?)''', 
            (peer_ip, peer_port, datetime.now())
        )
        conn.commit()  # Commit after inserting the peer

        # Get peer id
        cursor.execute('SELECT peer_id FROM Peers WHERE ip = ? AND port = ?', (peer_ip, peer_port))
        peer = cursor.fetchone()
        if peer:
            peer_id = peer[0]
        else:
            return jsonify({"error": "Peer registration failed"}), 500

        # Register files and their pieces
        for file in files:
            file_hash = file.get("file_hash")
            pieces = file.get("pieces", [])

            # Check if file exists in the Files table
            cursor.execute(
                '''SELECT file_id FROM Files WHERE file_hash = ?''', 
                (file_hash,)
            )
            result = cursor.fetchone()
            if not result:
                return jsonify({"error": f"File {file_hash} not found"}), 404

            file_id = result[0]

            # Register pieces associated with the file
            for piece_index in pieces:
                cursor.execute(
                   '''INSERT OR IGNORE INTO File_Pieces (file_id, peer_id, piece_index) 
                      VALUES (?, ?, ?)''', 
                   (file_id, peer_id, piece_index)
                )

        conn.commit()  # Commit all changes
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    return jsonify({"status": "success"})


@app.route('/peers', methods=['GET'])
def get_peers():
    
    file_hash = request.args.get("file_hash")
    if not file_hash:
        return jsonify({"error": "file_hash is required"}), 400

    conn = connect_db()
    cursor = conn.cursor()

    # Get the file ID
    cursor.execute(
        '''
        SELECT file_id FROM Files WHERE file_hash = ?
        ''', (file_hash,)
    )
    result = cursor.fetchone()
    if not result:
        return jsonify({"error": "File not found"}), 404

    file_id = result[0]

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

    conn.close()

    # Structure the response
    response = {
        "peers": [
            {"ip": ip, "port": port, "piece_index": piece_index}
            for ip, port, piece_index in peers
        ]
    }
    return jsonify(response)

if __name__ == "__main__":
    app.run(port=5500)
