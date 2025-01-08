import requests
import socket
import threading
import os
import hashlib
import math
import sys
import logging
sys.path.append('/Users/xuanloc/Documents/GitHub/torrent-file-sharing/Tracker')
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
directory = os.getcwd()
from database import add_file, get_file_id_by_hash, add_file_piece
DOWNLOAD_DIR = os.getcwd()
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

def start_server():
    peer_ip = input("Enter your IP address: ").strip()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((peer_ip, PEER_PORT))
        server.listen(5)
        print(f"Peer server started on {peer_ip}:{PEER_PORT}")

        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

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

def register_and_upload_file(file_path, port, ip):
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
        "ip": ip,
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
        print(f"HTTP error during tracker registration for {file_path}: {e}")
        print(f"Response content: {e.response.text}")
    except requests.RequestException as e:
        print(f"Error communicating with tracker for {file_path}: {e}")



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

def get_available_files():
    try:
        response = requests.get(f"{TRACKER_URL}/files")
        response.raise_for_status()
        return response.json() 
    except requests.RequestException as e:
        logging.error(f"Error querying tracker for available files: {e}")
        return None


def get_file_info(file_hash):
    try:
        response = requests.get(f"{TRACKER_URL}/peers", params={"file_hash": file_hash})
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error querying tracker: {e}")
        return None


def download_piece(peer_ip, peer_port, piece_index, file_name):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect((peer_ip, int(peer_port)))
            logging.info(f"Connected to peer {peer_ip}:{peer_port} for piece {piece_index} of {file_name}")
            client.sendall(f"GET {piece_index} {file_name}\n".encode())
            data = b""
            while chunk := client.recv(BUFFER_SIZE):
                data += chunk
            file_pieces[piece_index] = data
            logging.info(f"Successfully downloaded piece {piece_index} from {peer_ip}:{peer_port}")
            return True
    except Exception as e:
        logging.error(f"Error downloading piece {piece_index} from {peer_ip}:{peer_port}: {e}")
        return False


def download_file_combined(file_hashes, file_name, total_pieces):
    aggregated_pieces = {}
    for file_hash in file_hashes:
        file_info = get_file_info(file_hash)
        if not file_info:
            logging.error(f"Failed to retrieve file information for hash {file_hash}. Skipping...")
            continue
        logging.info(f"File info received for hash {file_hash}: {file_info}")

        for piece_index, peers in file_info.get("pieces", {}).items():
            if piece_index not in aggregated_pieces:
                aggregated_pieces[piece_index] = set()
            aggregated_pieces[piece_index].update(peers)

    missing_pieces = set(range(total_pieces)) - set(map(int, aggregated_pieces.keys()))
    if missing_pieces:
        logging.error(f"Error: Missing pieces {missing_pieces}. Cannot complete download.")
        return

    threads = []
    for piece_index, peers in aggregated_pieces.items():
        for peer in peers:
            peer_ip, peer_port = peer.split(":")
            thread = threading.Thread(
                target=lambda idx=piece_index: (
                    missing_pieces.discard(idx) if download_piece(peer_ip, peer_port, idx, file_name) else None
                )
            )
            threads.append(thread)
            thread.start()
            break  

    for thread in threads:
        thread.join()

    if missing_pieces:
        logging.error(f"Failed to download pieces: {missing_pieces}")
        return

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    output_file = os.path.join(DOWNLOAD_DIR, file_name)
    with open(output_file, "wb") as f:
        for piece_index in sorted(file_pieces.keys()):
            f.write(file_pieces[piece_index])

    logging.info(f"Download completed for {file_name}")
    logging.info(f"File saved as {output_file}")

def main():
    while True:
        print("\n=== Torrent CLI ===")
        print("1. Register Peer")
        print("2. Upload File")
        print("3. Start Peer Server")
        print("4. Download")
        print("5. Exit")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            register_peer()
        elif choice == "2":
            print("Please input your IP address: ")
            ip = str(input()).strip()

            selected_files = select_files()

            if not selected_files:
                print("No files selected for upload. Exiting...")
                exit()

            for file_path in selected_files:
                register_and_upload_file(file_path, PEER_PORT, ip)

        elif choice == "3":
            start_server()
        elif choice == "4":
            available_files = get_available_files()
            if not available_files:
                logging.error("No files available for download.")
                exit()

            print("Available files for download:")
            for file in available_files:
                print(f"- {file['file_name']} (Hash: {file['file_hash']}, Pieces: {file['total_pieces']})")

            selected_names = input("Enter the names of the files you want to download (comma-separated): ")
            selected_names = [name.strip() for name in selected_names.split(",")]

            selected_files = [file for file in available_files if file["file_name"] in selected_names]
            print(selected_files)
            if not selected_files:
                logging.info("No valid file names entered. Exiting...")
                exit()

            file_groups = {}
            for file in selected_files:
                file_hash = file["file_hash"]
                file_name = file["file_name"]
                total_pieces = file["total_pieces"]
                file_groups.setdefault((file_name, total_pieces), []).append(file_hash)

            for (file_name, total_pieces), file_hashes in file_groups.items():
                logging.info(f"Starting download for {file_name} with hashes {file_hashes}")
                download_file_combined(file_hashes, file_name, total_pieces)

        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
