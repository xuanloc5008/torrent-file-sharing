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

PEER_PORT = 5503 
TRACKER_URL = "http://localhost:5500/upload"  
BUFFER_SIZE = 1024

file_pieces = {}
piece_status = {}

def calculate_file_hash(file_path):
    sha1 = hashlib.sha1()
    sha1.update(str(PEER_PORT).encode())
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
        request = conn.recv(BUFFER_SIZE).decode().strip()

        command, *args = request.split()

        if command == "GET":
            piece_index = int(args[0])
            file_name = args[1]  

            print(f"Requested piece {piece_index} for file {file_name}")
            if file_name in file_pieces:
                if piece_index in file_pieces[file_name]:
                    conn.sendall(file_pieces[file_name][piece_index])
                    print(f"Sent piece {piece_index} of {file_name} to {addr}")
                else:
                    conn.sendall(b"ERROR: Piece not found")
                    print(f"Piece {piece_index} of {file_name} not found, sending error to {addr}")
            else:
                conn.sendall(b"ERROR: File not found")
                print(f"File {file_name} not found, sending error to {addr}")
        elif command == "STATUS":
            conn.sendall(str(piece_status).encode())
            print(f"Sent piece status to {addr}")
        else:
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



def split_file_into_pieces(file_path, piece_length, file_name):
    global file_pieces
    file_pieces[file_name] = {}
    pieces = []

    with open(file_path, "rb") as file:
        index = 0
        while chunk := file.read(piece_length):
            if piece_status[file_name][index] == 1:
                file_pieces[file_name][index] = chunk
                pieces.append(index)
            index += 1

    print(f"File pieces for {file_name}: {file_pieces[file_name]}") 
    return pieces

def manually_enter_piece_status(total_pieces):
    while True:
        try:
            status_input = input(
                f"Enter the piece status for {total_pieces} pieces (e.g., '1,0,1,...'): "
            )
            status_list = [int(x) for x in status_input.split(",")]
            if len(status_list) != total_pieces:
                raise ValueError("Invalid number of pieces.")
            if not all(x in (0, 1) for x in status_list):
                raise ValueError("Piece status must be 0 or 1.")
            return status_list
        except ValueError as e:
            print(f"Error: {e}. Please try again.")


def register_and_upload_file(file_path, port):
    piece_length = 1  
    file_size = os.path.getsize(file_path)
    total_pieces = math.ceil(file_size / piece_length)
    file_name = os.path.basename(file_path)
    print(f"Processing {file_name} with {total_pieces} pieces.")

    piece_status[file_name] = manually_enter_piece_status(total_pieces)

    pieces = split_file_into_pieces(file_path, piece_length, file_name)

    file_hash = calculate_file_hash(file_path)
    if not file_hash:
        print(f"Failed to calculate hash for {file_path}. Skipping...")
        return

    add_file(file_name, file_hash, piece_length, total_pieces)

    data = {
        "port": port,
        "files": [{
            "file_hash": file_hash,
            "pieces": pieces, 
        }]
    }

    try:
        response = requests.post(TRACKER_URL, json=data)
        response.raise_for_status()
        print(f"File {file_name} successfully registered with tracker:", response.json())
    except requests.HTTPError as e:
        print(f"HTTP error during tracker registration for {file_path}: {e}")
        print(f"Response content: {e.response.text}")
    except requests.RequestException as e:
        print(f"Error communicating with tracker for {file_path}: {e}")


def select_files():
    directory = os.getcwd() 
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

    if not files:
        print("No files found in the directory.")
        return []

    print("Available files:")
    for idx, file_name in enumerate(files, start=1):
        print(f"{idx}. {file_name}")

    while True:
        try:
            selected_indices = input("Enter the numbers of the files to upload (comma-separated): ")
            selected_indices = [int(x.strip()) - 1 for x in selected_indices.split(",")]
            selected_files = [os.path.join(directory, files[i]) for i in selected_indices]
            return selected_files
        except (ValueError, IndexError):
            print("Invalid input. Please enter valid numbers corresponding to the files.")



if __name__ == "__main__":
    selected_files = select_files()

    if not selected_files:
        print("No files selected for upload. Exiting...")
        exit()

    for file_path in selected_files:
        register_and_upload_file(file_path, PEER_PORT)

    print("Files and piece statuses:", piece_status)
    start_server(PEER_PORT)
    print("Peer is now ready to upload files.")
