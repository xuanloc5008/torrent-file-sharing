import socket
import threading
import requests
import os

# Configuration
TRACKER_URL = "http://127.0.0.1:8000"  # Tracker URL
BUFFER_SIZE = 1024  # Size of the data buffer for piece transmission
DOWNLOAD_DIR = "downloads"  # Directory to store downloaded pieces
OUTPUT_FILE = "downloaded_file.txt"  # Name of the final assembled file


def get_file_info(file_hash):
    """
    Queries the tracker for information about the file.

    Args:
        file_hash (str): The hash of the file to download.

    Returns:
        dict: A dictionary containing peer information and piece availability.
              Example format: {"pieces": {"1": ["127.0.0.1:5001"], "2": ["127.0.0.1:5002"]}, "file_size": 2048}
    """
    try:
        response = requests.get(f"{TRACKER_URL}/get_file_info", params={"file_hash": file_hash})
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error querying tracker: {e}")
        return None


def download_piece(peer_ip, peer_port, piece_index, save_dir):
    """
    Downloads a specific piece from a peer.

    Args:
        peer_ip (str): Peer IP address.
        peer_port (int): Peer port number.
        piece_index (int): Piece index to download.
        save_dir (str): Directory to save the downloaded piece.

    Returns:
        bool: True if the piece was downloaded successfully, False otherwise.
    """
    try:
        # Establish a connection with the peer
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect((peer_ip, peer_port))
            print(f"Connected to peer {peer_ip}:{peer_port}")

            # Send a request to get the specific piece
            request = f"GET {piece_index}"
            client.sendall(request.encode())

            # Save the received piece
            os.makedirs(save_dir, exist_ok=True)
            piece_path = os.path.join(save_dir, f"piece_{piece_index}")

            with open(piece_path, "wb") as piece_file:
                while True:
                    data = client.recv(BUFFER_SIZE)
                    if not data:
                        break
                    piece_file.write(data)

            print(f"Downloaded piece {piece_index} from {peer_ip}:{peer_port}")
            return True
    except Exception as e:
        print(f"Error downloading piece {piece_index} from {peer_ip}:{peer_port}: {e}")
        return False


def download_pieces_concurrently(file_info, save_dir):
    """
    Downloads all pieces concurrently from available peers.

    Args:
        file_info (dict): Information about the file (peers and pieces).
                          Example: {"pieces": {"1": ["127.0.0.1:5001"], "2": ["127.0.0.1:5002"]}}
        save_dir (str): Directory to save downloaded pieces.

    Returns:
        None
    """
    threads = []
    for piece_index, peers in file_info["pieces"].items():
        # Pick the first peer that has the piece
        peer = peers[0]
        peer_ip, peer_port = peer.split(":")  # Assuming peer is in "IP:PORT" format

        # Start a thread to download the piece
        thread = threading.Thread(target=download_piece, args=(peer_ip, int(peer_port), piece_index, save_dir))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    print("All pieces downloaded.")


def assemble_file(pieces_dir, output_file, total_pieces):
    """
    Assembles downloaded pieces into a complete file.

    Args:
        pieces_dir (str): Directory containing the downloaded pieces.
        output_file (str): Path to save the assembled file.
        total_pieces (int): Total number of pieces.

    Returns:
        None
    """
    try:
        with open(output_file, "wb") as output:
            for piece_index in range(1, total_pieces + 1):
                piece_path = os.path.join(pieces_dir, f"piece_{piece_index}")
                if not os.path.exists(piece_path):
                    print(f"Missing piece {piece_index}, assembly failed.")
                    return
                with open(piece_path, "rb") as piece_file:
                    output.write(piece_file.read())
        print(f"File assembled as {output_file}")
    except Exception as e:
        print(f"Error assembling file: {e}")


def download_file(file_hash):
    """
    Downloads a file by querying the tracker, downloading pieces, and assembling the file.

    Args:
        file_hash (str): Hash of the file to download.

    Returns:
        None
    """
    # Query the tracker for file information
    file_info = get_file_info(file_hash)
    if not file_info:
        print("Failed to retrieve file information from tracker.")
        return

    # Extract file details
    total_pieces = len(file_info["pieces"])

    # Download all pieces
    download_pieces_concurrently(file_info, DOWNLOAD_DIR)

    # Assemble the final file
    assemble_file(DOWNLOAD_DIR, OUTPUT_FILE, total_pieces)


if __name__ == "__main__":
    # Example file hash to download
    file_hash = "example_file_hash_1234"

    # Start the download process
    download_file(file_hash)
