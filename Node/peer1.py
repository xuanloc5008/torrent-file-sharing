import requests
import socket
import threading
import os
import hashlib
import math
import sys
import logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

TRACKER_URL = "https://ecf8-14-241-225-112.ngrok-free.app"
PEER_PORT = 5501
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


def register_peer():
    peer_ip = input("Enter your IP address: ").strip()
    data = {
        "ip": peer_ip,
        "port": PEER_PORT,
        "files": []
    }
    try:
        response = requests.post(f"{TRACKER_URL}/announce", json=data)
        response.raise_for_status()
        print("Registered with tracker successfully:", response.json())
    except requests.HTTPError as e:
        print(f"HTTP error during tracker registration: {e}")
    except requests.RequestException as e:
        print(f"Error communicating with tracker: {e}")


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


def upload_file():
    def select_files():
        directory = os.getcwd()
        files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

        if not files:
            print("No files found in the current directory.")
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

    selected_files = select_files()

    if not selected_files:
        print("No files selected for upload. Exiting...")
        return

    for file_path in selected_files:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue

        piece_length = 1  
        file_size = os.path.getsize(file_path)
        total_pieces = math.ceil(file_size / piece_length)
        file_name = os.path.basename(file_path)

        print(f"Processing {file_name} with {total_pieces} pieces.")
        piece_status[file_name] = manually_enter_piece_status(total_pieces)

        pieces = split_file_into_pieces(file_path, piece_length, file_name)
        file_hash = calculate_file_hash(file_path)

        if not file_hash:
            print(f"Failed to calculate hash for {file_name}. Skipping...")
            continue

        data = {
            "port": PEER_PORT,
            "ip": input("Enter your IP address: ").strip(),
            "files": [{
                "file_hash": file_hash,
                "pieces": pieces,
            }]
        }

        try:
            response = requests.post(f"{TRACKER_URL}/upload", json=data)
            response.raise_for_status()
            print(f"File {file_name} successfully registered with tracker:", response.json())
        except requests.HTTPError as e:
            print(f"HTTP error during tracker registration for {file_name}: {e}")
            print(f"Response content: {e.response.text}")
        except requests.RequestException as e:
            print(f"Error communicating with tracker for {file_name}: {e}")

    print("Files and piece statuses:", piece_status)


def start_server():
    peer_ip = input("Enter your IP address: ").strip()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((peer_ip, PEER_PORT))
        server.listen(5)
        print(f"Peer server started on {peer_ip}:{PEER_PORT}")

        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


def handle_client(conn, addr):
    try:
        request = conn.recv(BUFFER_SIZE).decode().strip()
        command, *args = request.split()

        if command == "GET":
            piece_index = int(args[0])
            file_name = args[1]
            if file_name in file_pieces and piece_index in file_pieces[file_name]:
                conn.sendall(file_pieces[file_name][piece_index])
            else:
                conn.sendall(b"ERROR: Piece not found")
        else:
            conn.sendall(b"ERROR: Invalid request")
    finally:
        conn.close()


def main():
    while True:
        print("\n=== Torrent CLI ===")
        print("1. Register Peer")
        print("2. Upload File")
        print("3. Start Peer Server")
        print("4. Exit")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            register_peer()
        elif choice == "2":
            upload_file()
        elif choice == "3":
            start_server()
        elif choice == "4":
            print("Exiting... Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
