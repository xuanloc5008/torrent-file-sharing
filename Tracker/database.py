import mysql.connector
from mysql.connector import Error
from datetime import datetime

DB_CONFIG = {
    'host': 'truntrun.ddns.net',
    'user': 'tuanemtramtinh',
    'password': 'TuanAnh_0908',
    'database': 'assignment',
    'port': 3306  
}

# Connect to the database
def connect_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
        raise

# Initialize database and tables
def initialize_database():
    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Create database if it doesn't exist
        cursor.execute("CREATE DATABASE IF NOT EXISTS assignment")
        conn.database = "assignment"  # Select the database

        # Create Files table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Files (
            file_id INT AUTO_INCREMENT PRIMARY KEY,
            file_name VARCHAR(255) NOT NULL,
            file_hash VARCHAR(64) UNIQUE NOT NULL,
            piece_length INT NOT NULL,
            total_pieces INT NOT NULL
        )
        ''')

        # Create Peers table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Peers (
            peer_id INT AUTO_INCREMENT PRIMARY KEY,
            ip VARCHAR(45) NOT NULL,
            port INT NOT NULL,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create File_Pieces table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS File_Pieces (
            file_id INT,
            peer_id INT,
            piece_index INT,
            PRIMARY KEY (file_id, peer_id, piece_index),
            FOREIGN KEY (file_id) REFERENCES Files(file_id) ON DELETE CASCADE,
            FOREIGN KEY (peer_id) REFERENCES Peers(peer_id) ON DELETE CASCADE
        )
        ''')

        conn.commit()
        print("Database and tables initialized successfully!")
    except Error as e:
        print(f"Error initializing database: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# Add a new file
def add_file(file_name, file_hash, piece_length, total_pieces):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO Files (file_name, file_hash, piece_length, total_pieces)
        VALUES (%s, %s, %s, %s)
        ''', (file_name, file_hash, piece_length, total_pieces))
        conn.commit()
        print(f"File '{file_name}' added successfully!")
    except mysql.connector.IntegrityError:
        print(f"File with hash {file_hash} already exists.")
    finally:
        cursor.close()
        conn.close()

# Add a new peer
def add_peer(ip, port):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO Peers (ip, port, last_active)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE last_active = %s
    ''', (ip, port, datetime.now(), datetime.now()))
    conn.commit()
    print(f"Peer {ip}:{port} added/updated successfully!")
    cursor.close()
    conn.close()

# Add a new file piece
def add_file_piece(file_id, peer_id, piece_index):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO File_Pieces (file_id, peer_id, piece_index)
    VALUES (%s, %s, %s)
    ''', (file_id, peer_id, piece_index))
    conn.commit()
    print(f"Piece {piece_index} for file_id {file_id} and peer_id {peer_id} added successfully!")
    cursor.close()
    conn.close()

# Get peers with a specific file piece
def get_peers_with_piece(file_id, piece_index):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT Peers.ip, Peers.port
    FROM File_Pieces
    INNER JOIN Peers ON File_Pieces.peer_id = Peers.peer_id
    WHERE File_Pieces.file_id = %s AND File_Pieces.piece_index = %s
    ''', (file_id, piece_index))
    peers = cursor.fetchall()
    cursor.close()
    conn.close()
    return peers

# Get file ID by file hash
def get_file_id_by_hash(file_hash):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT file_id FROM Files WHERE file_hash = %s
    ''', (file_hash,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else None
