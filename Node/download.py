import requests
import os
import socket
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

TRACKER_URL = "http://127.0.0.1:5500"  # URL of the tracker
BUFFER_SIZE = 1024  # Buffer size for downloading pieces
DOWNLOAD_DIR = os.getcwd()  # Directory where the file will be saved
file_pieces = {}  # Dictionary to store downloaded pieces


def get_available_files():
    """
    Retrieve the list of available files from the tracker.
    """
    try:
        response = requests.get(f"{TRACKER_URL}/files")
        response.raise_for_status()
        return response.json()  # Assuming the response contains a list of files
    except requests.RequestException as e:
        logging.error(f"Error querying tracker for available files: {e}")
        return None


def get_file_info(file_hash):
    """
    Retrieve peer information for a specific file hash from the tracker.
    """
    try:
        response = requests.get(f"{TRACKER_URL}/peers", params={"file_hash": file_hash})
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error querying tracker: {e}")
        return None


def download_piece(peer_ip, peer_port, piece_index, file_name):
    """
    Downloads a specific piece from the given peer.
    """
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
    """
    Downloads a file by aggregating piece information from multiple file hashes.
    """
    # Step 1: Aggregate piece information across all hashes
    aggregated_pieces = {}
    for file_hash in file_hashes:
        file_info = get_file_info(file_hash)
        if not file_info:
            logging.error(f"Failed to retrieve file information for hash {file_hash}. Skipping...")
            continue
        logging.info(f"File info received for hash {file_hash}: {file_info}")

        # Merge piece information
        for piece_index, peers in file_info.get("pieces", {}).items():
            if piece_index not in aggregated_pieces:
                aggregated_pieces[piece_index] = set()
            aggregated_pieces[piece_index].update(peers)

    # Step 2: Check if we have all pieces
    missing_pieces = set(range(total_pieces)) - set(map(int, aggregated_pieces.keys()))
    if missing_pieces:
        logging.error(f"Error: Missing pieces {missing_pieces}. Cannot complete download.")
        return

    # Step 3: Start downloading pieces
    threads = []
    for piece_index, peers in aggregated_pieces.items():
        for peer in peers:
            peer_ip, peer_port = peer.split(":")
            # Start a thread to download the piece
            thread = threading.Thread(
                target=lambda idx=piece_index: (
                    missing_pieces.discard(idx) if download_piece(peer_ip, peer_port, idx, file_name) else None
                )
            )
            threads.append(thread)
            thread.start()
            break  # Assign the piece to one peer and move to the next piece

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Step 4: Verify all pieces were downloaded
    if missing_pieces:
        logging.error(f"Failed to download pieces: {missing_pieces}")
        return

    # Step 5: Write pieces to file
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    output_file = os.path.join(DOWNLOAD_DIR, file_name)
    with open(output_file, "wb") as f:
        for piece_index in sorted(file_pieces.keys()):
            f.write(file_pieces[piece_index])

    logging.info(f"Download completed for {file_name}")
    logging.info(f"File saved as {output_file}")


if __name__ == "__main__":
    # Step 1: Get the list of available files from the tracker
    available_files = get_available_files()
    if not available_files:
        logging.error("No files available for download.")
        exit()

    # Step 2: Display available files
    print("Available files for download:")
    for file in available_files:
        print(f"- {file['file_name']} (Hash: {file['file_hash']}, Pieces: {file['total_pieces']})")

    # Step 3: Let user select files by name
    selected_names = input("Enter the names of the files you want to download (comma-separated): ")
    selected_names = [name.strip() for name in selected_names.split(",")]

    # Filter files by selected names
    selected_files = [file for file in available_files if file["file_name"] in selected_names]

    if not selected_files:
        logging.info("No valid file names entered. Exiting...")
        exit()

    # Step 4: Group file hashes for the same file
    file_groups = {}
    for file in selected_files:
        file_hash = file["file_hash"]
        file_name = file["file_name"]
        total_pieces = file["total_pieces"]
        file_groups.setdefault((file_name, total_pieces), []).append(file_hash)

    # Step 5: Process each file group
    for (file_name, total_pieces), file_hashes in file_groups.items():
        logging.info(f"Starting download for {file_name} with hashes {file_hashes}")
        download_file_combined(file_hashes, file_name, total_pieces)
