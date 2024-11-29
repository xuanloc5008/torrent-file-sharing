import sqlite3
from datetime import datetime

DB_NAME = "D:/web_git/btl/torrent-file-sharing/tracker.db"

def connect_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        raise


def initialize_database():
    conn = connect_db()
    cursor = conn.cursor()

    # Create the Files table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Files (
        file_id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT NOT NULL,
        file_hash TEXT UNIQUE NOT NULL,
        piece_length INTEGER NOT NULL,
        total_pieces INTEGER NOT NULL
    )
    ''')

    # Create the Peers table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Peers (
        peer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT NOT NULL,
        port INTEGER NOT NULL,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create the File_Pieces table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS File_Pieces (
        file_id INTEGER,
        peer_id INTEGER,
        piece_index INTEGER,
        PRIMARY KEY (file_id, peer_id, piece_index),
        FOREIGN KEY (file_id) REFERENCES Files(file_id) ON DELETE CASCADE,
        FOREIGN KEY (peer_id) REFERENCES Peers(peer_id) ON DELETE CASCADE
    )
    ''')

    conn.commit()
    conn.close()

def add_file(file_name, file_hash, piece_length, total_pieces):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO Files (file_name, file_hash, piece_length, total_pieces)
        VALUES (?, ?, ?, ?)
        ''', (file_name, file_hash, piece_length, total_pieces))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"File with hash {file_hash} already exists.")
    finally:
        conn.close()

def add_peer(ip, port):
    
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR IGNORE INTO Peers (ip, port, last_active)
    VALUES (?, ?, ?)
    ''', (ip, port, datetime.now()))
    conn.commit()
    conn.close()

def update_peer_activity(peer_id):
    
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE Peers SET last_active = ? WHERE peer_id = ?
    ''', (datetime.now(), peer_id))
    conn.commit()
    conn.close()

def add_file_piece(file_id, peer_id, piece_index):
    
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR IGNORE INTO File_Pieces (file_id, peer_id, piece_index)
    VALUES (?, ?, ?)
    ''', (file_id, peer_id, piece_index))
    conn.commit()
    conn.close()

def get_peers_with_piece(file_id, piece_index):
   
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT Peers.ip, Peers.port
    FROM File_Pieces
    INNER JOIN Peers ON File_Pieces.peer_id = Peers.peer_id
    WHERE File_Pieces.file_id = ? AND File_Pieces.piece_index = ?
    ''', (file_id, piece_index))
    peers = cursor.fetchall()
    conn.close()
    return peers

def get_file_id_by_hash(file_hash):
    
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT file_id FROM Files WHERE file_hash = ?
    ''', (file_hash,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None
