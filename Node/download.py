import socket
import threading
import requests
import os

TRACKER_URL = "http://127.0.0.1:5500"  
BUFFER_SIZE = 1024
DOWNLOAD_DIR = "D:/web_git/btl/torrent-file-sharing/Node"  
FINAL_FILE_NAME = ""

file_pieces = {}

def get_file_info(file_hash):
    try:
        response = requests.get(f"{TRACKER_URL}/peers", params={"file_hash": file_hash})
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error querying tracker: {e}")
        return None


def download_piece_and_write_to_file(peer_ip, peer_port, piece_index, output_file):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect((peer_ip, peer_port))
            print(f"Connected to peer {peer_ip}:{peer_port}")

            request = f"GET {piece_index}\n"
            client.sendall(request.encode())

            piece_data = b""
            while True:
                data = client.recv(BUFFER_SIZE)
                if not data:
                    break
                piece_data += data

            file_pieces[piece_index] = piece_data
            print(f"Piece {piece_index} downloaded and stored in memory")
            return True
    except Exception as e:
        print(f"Error downloading piece {piece_index} from {peer_ip}:{peer_port}: {e}")
        return False


def download_pieces_concurrently(file_info, output_file):
    threads = []
    for piece_index, peers in file_info["pieces"].items():
        # Pick the first peer that has the piece
        peer = peers[0]
        peer_ip, peer_port = peer.split(":")  

        thread = threading.Thread(target=download_piece_and_write_to_file, args=(peer_ip, int(peer_port), int(piece_index), output_file))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    with open(output_file, "wb") as final_file:
        for piece_index in range(len(file_info["pieces"])):
            final_file.write(file_pieces[piece_index])


def download_file(file_hash):
    global FINAL_FILE_NAME

    file_info = get_file_info(file_hash)
    if not file_info:
        print("Failed to retrieve file information from tracker.")
        return
    print(file_info)

    FINAL_FILE_NAME = file_info.get("file_name", "downloaded_file")  

    output_file_path = os.path.join(DOWNLOAD_DIR, FINAL_FILE_NAME)

    total_pieces = len(file_info["pieces"])

    download_pieces_concurrently(file_info, output_file_path)

    print(f"File downloaded and saved as {output_file_path}")


if __name__ == "__main__":
    file_hash = "ae8fe380dd9aa5a7a956d9085fe7cf6b87d0d028"

    download_file(file_hash)
