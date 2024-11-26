import socket
import threading
import requests
import os
import sys
import hashlib
import math
import time

sys.path.append('D:/web_git/btl/torrent-file-sharing/Tracker')
from database import add_file

PEER_PORT = 5501 
TRACKER_URL = "http://localhost:5500/upload"  
BUFFER_SIZE = 1024

file_pieces = {}

def calculate_file_hash(file_path):
    sha1 = hashlib.sha1()
    try:
        with open(file_path, "rb") as file:
            while chunk := file.read(8192):
                sha1.update(chunk)
        return sha1.hexdigest()
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except Exception as e:
        print(f"Error calculating file hash: {e}")
        return None

def handle_client(conn, addr):
    try:
        print(f"Connection from {addr}")
        request = conn.recv(BUFFER_SIZE).decode()
        command, piece_id = request.strip().split()  

        if command == "GET" and piece_id.isdigit():
            piece_id = int(piece_id)
            if piece_id in file_pieces:
                conn.sendall(file_pieces[piece_id])  
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
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", port))
        server.listen(5)
        print(f"Peer server started on port {port}")

        while True:
            conn, addr = server.accept()
            print(f"Accepted connection from {addr}")
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

def split_file_into_pieces(file_path, piece_length):
    pieces = []
    with open(file_path, "rb") as file:
        index = 0
        while chunk := file.read(piece_length):
            file_pieces[index] = chunk
            pieces.append(index)
            index += 1
    return pieces

def register_file_with_tracker():
    file_path = "D:/web_git/btl/torrent-file-sharing/Node2/example.txt"
    piece_length = 1
    
    file_size = os.path.getsize(file_path)
    total_pieces = math.ceil(file_size / piece_length)
    print(f"Total pieces: {total_pieces}")
    
    # Split file into pieces
    pieces = split_file_into_pieces(file_path, piece_length)

    file_hash = calculate_file_hash(file_path)
    if not file_hash:
        print("Failed to calculate file hash. Exiting.")
        return

    # Prepare the file status (assuming all pieces are available initially)
    piece_status = [1, 0, 1, 0] 

    add_file(os.path.basename(file_path), file_hash, piece_length, total_pieces)

    data = {
        "port": PEER_PORT,
        "files": [{
            "file_hash": file_hash,
            "pieces": pieces,
            "piece_status": piece_status  # Add piece status here
        }]
    }

    try:
        response = requests.post(TRACKER_URL, json=data)
        response.raise_for_status()  
        print("File successfully registered with tracker:", response.json())
    except requests.HTTPError as e:
        print(f"HTTP error during tracker registration: {e}")
        print(f"Response content: {e.response.text}")
    except requests.RequestException as e:
        print(f"Error communicating with tracker: {e}")

if __name__ == "__main__":
    os.makedirs("pieces", exist_ok=True) 

    register_file_with_tracker()
    start_server(PEER_PORT)
    print("Peer is now ready to upload the file.")
