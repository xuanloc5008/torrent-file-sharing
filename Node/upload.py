import socket
import threading
import requests
import os
import sys
sys.path.append('D:/web_git/btl/torrent-file-sharing/Tracker')  
from database import add_file


PIECE_DIR = "pieces"
PEER_PORT = 6881 
FILES = [
    {"file_hash": "abc123", "pieces": [0, 1, 2, 3, 4]} 
]
TRACKER_URL = "http://localhost:5500/announce"  
BUFFER_SIZE = 1024  

def handle_client(conn, addr):
    try:
        print(f"Connection from {addr}")

        request = conn.recv(BUFFER_SIZE).decode()
        command, piece_id = request.split()

        # Ensure the command is a valid "GET PIECE"
        if command == "GET" and piece_id.isdigit():
            piece_path = os.path.join(PIECE_DIR, f"piece_{piece_id}")
            
            # Check if the requested piece exists
            if os.path.exists(piece_path):
                with open(piece_path, "rb") as piece_file:
                    # Send the piece in chunks
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
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("0.0.0.0", port))
        server.listen()

        print(f"Peer server started on port {port}")

        while True:
            conn, addr = server.accept()
            # Handle each client in a separate thread
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()

def register_with_tracker():
    # Ensure the file is added to the tracker database
    file_hash = "abc123"
    file_name = "example_file.txt"  
    piece_length = 1024 
    total_pieces = 5  

    add_file(file_name, file_hash, piece_length, total_pieces)

    data = {
        "port": PEER_PORT,
        "files": FILES
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
    threading.Thread(target=start_server, args=(PEER_PORT,)).start()
    register_with_tracker()
    print("Peer is now registered and ready to upload.")
