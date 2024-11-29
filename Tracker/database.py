import mysql.connector
from mysql.connector import Error
from datetime import datetime

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'network',
    'password': 'baykhivadegia',
    'database': 'assignment',
    'port': 3300  # Ensure your container exposes this port
}

# Connect to the Database
def connect_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("Connection successful:", conn)
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
        raise

# Initialize Database and Tables
def initialize_database():
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            port=DB_CONFIG['port']
        )
        cursor = conn.cursor()

        # Create Database if not exists
        print("Creating database...")
        cursor.execute("CREATE DATABASE IF NOT EXISTS assignment")
        print("Database created (if not exists).")
        conn.database = "assignment"  # Explicitly select the database

        # Create Files table
        print("Creating Files table...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Files (
            file_id INT AUTO_INCREMENT PRIMARY KEY,
            file_name VARCHAR(255) NOT NULL,
            file_hash VARCHAR(64) UNIQUE NOT NULL,
            piece_length INT NOT NULL,
            total_pieces INT NOT NULL
        )
        ''')
        print("Files table created.")

        # Create Peers table
        print("Creating Peers table...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Peers (
            peer_id INT AUTO_INCREMENT PRIMARY KEY,
            ip VARCHAR(45) NOT NULL,
            port INT NOT NULL,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        print("Peers table created.")

        # Create File_Pieces table
        print("Creating File_Pieces table...")
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
        print("File_Pieces table created.")

        conn.commit()
        print("Database and tables initialized successfully!")
    except Error as e:
        print(f"Error initializing database: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# Insert a new file
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

# Insert a new peer
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

# Insert a new file piece
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

# Main Function to Test the Script
if __name__ == "__main__":
    try:
        # Initialize the database and tables
        initialize_database()

        # Add test data
        add_file("example_file.txt", "abc123", 512, 10)
        add_peer("192.168.1.1", 8080)

        # Add a file piece
        file_id = get_file_id_by_hash("abc123")
        if file_id:
            add_file_piece(file_id, 1, 0)  # Assuming peer_id = 1

        # Fetch peers with a specific file piece
        peers = get_peers_with_piece(file_id, 0)
        print(f"Peers with piece 0 of file_id {file_id}: {peers}")
    except Exception as e:
        print(f"Error: {e}")
