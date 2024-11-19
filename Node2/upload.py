import socket
import threading
import requests
import os
import sys
import hashlib
import math

sys.path.append('D:/web_git/btl/torrent-file-sharing/Tracker')
from database import add_file

PIECE_DIR = "pieces"
PIECE_SIZE = 1
PEER_PORT = 6882  
TRACKER_URL = "http://localhost:5500/announce"  
BUFFER_SIZE = 1024

def calculate_file_hash(file_path):
    """
    Calculates the SHA-1 hash of the given file.
    """
    sha1 = hashlib.sha1()
    try:
        with open(file_path, "rb") as file:
            while chunk := file.read(8192):  # Read file in chunks
                sha1.update(chunk)
        return sha1.hexdigest()
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except Exception as e:
        print(f"Error calculating file hash: {e}")
        return None

def handle_client(conn, addr):
    """
    Handles incoming requests from peers to upload a file piece.
    """
    try:
        print(f"Connection from {addr}")
        request = conn.recv(BUFFER_SIZE).decode()
        command, piece_id = request.split()

        if command == "GET" and piece_id.isdigit():
            piece_path = os.path.join(PIECE_DIR, f"piece_{piece_id}")
            if os.path.exists(piece_path):
                with open(piece_path, "rb") as piece_file:
                    while chunk := piece_file.read(BUFFER_SIZE):
                        conn.sendall(chunk)
                print(f"Sent piece {piece_id} to {addr}")
            else:
                print(f"Piece {piece_id} not found for {addr}")
                conn.sendall(b"ERROR: Piece not found")
        else:
            print(f"Invalid request from {addr}")
            conn.sendall(b"ERROR: Invalid request")
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        conn.close()

def start_server(port):
    """
    Starts the peer server to listen for incoming connections.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("0.0.0.0", port))
        server.listen()
        print(f"Peer server started on port {port}")

        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

def split_file_into_pieces(file_path, piece_length):
    pieces = []
    with open(file_path, "rb") as file:  # Open in binary mode
        while chunk := file.read(piece_length):
            pieces.append(chunk)
    return pieces

def register_with_tracker():
    """
    Registers the file with the tracker.
    """
    file_path = "D:/web_git/btl/torrent-file-sharing/Node/example.txt"  # Specify the actual file path
    piece_length = 1  # Length of each piece (in bytes)
    total_pieces = os.path.getsize(file_path) // piece_length + \
               (1 if os.path.getsize(file_path) % piece_length != 0 else 0)
    pieces = split_file_into_pieces(file_path, piece_length)
    print(f"Total pieces: {total_pieces}")
    for i, piece in enumerate(pieces):
        print(f"Piece {i}: {piece.decode()}")


    file_hash = calculate_file_hash(file_path)
    if not file_hash:
        print("Failed to calculate file hash. Exiting.")
        return

    # Calculate total pieces
    try:
        file_size = os.path.getsize(file_path)
        total_pieces = math.ceil(file_size / piece_length)
        total_pieces = max(total_pieces, 1)  # Ensure at least one piece
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return
    except Exception as e:
        print(f"Error getting file size: {e}")
        return

    # Add the file to the tracker's database
    add_file(os.path.basename(file_path), file_hash, piece_length, total_pieces)

    # Register with the tracker
    data = {
        "port": PEER_PORT,
        "files": [{"file_hash": file_hash, "pieces": list(range(total_pieces))}]
    }

    try:
        response = requests.post(TRACKER_URL, json=data)
        response.raise_for_status()
        print("Registered with tracker successfully:", response.json())
    except requests.HTTPError as e:
        print(f"HTTP error during tracker registration: {e}")
        print(f"Response content: {e.response.text}")
    except requests.RequestException as e:
        print(f"Error communicating with tracker: {e}")

if __name__ == "__main__":
    # Ensure the pieces directory exists
    os.makedirs(PIECE_DIR, exist_ok=True)

    # Start the peer server in a separate thread
    threading.Thread(target=start_server, args=(PEER_PORT,), daemon=True).start()

    # Register the file with the tracker
    register_with_tracker()

    print("Peer is now registered and ready to upload.")
