import threading
import socket
import os

PIECE_DIR = "pieces"  # Directory to save the pieces
BUFFER_SIZE = 1024  # Buffer size for receiving data

def download_piece(peer, piece_id):
    """
    Connects to a peer to download a specific piece.
    Saves the piece data to disk.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)  # Set a timeout for the connection
            s.connect((peer['ip'], peer['port']))
            s.sendall(f"GET PIECE {piece_id}".encode())

            # Receive data in chunks until done
            piece_data = b""
            while True:
                data = s.recv(BUFFER_SIZE)
                if not data:
                    break
                piece_data += data

            # Save the piece to a file
            os.makedirs(PIECE_DIR, exist_ok=True)
            with open(f"{PIECE_DIR}/piece_{piece_id}", "wb") as piece_file:
                piece_file.write(piece_data)
            
            print(f"Downloaded piece {piece_id} from {peer['ip']}:{peer['port']}")
    except (socket.error, socket.timeout) as e:
        print(f"Failed to download piece {piece_id} from {peer['ip']}:{peer['port']} - {e}")

def start_download(peers, pieces):
    threads = []
    for piece_id in pieces:
        for peer in peers:
            thread = threading.Thread(target=download_piece, args=(peer, piece_id))
            threads.append(thread)
            thread.start()
    
    # Wait for all threads to finish
    for thread in threads:
        thread.join()
    
    print("Download complete")

# Example usage
if __name__ == "__main__":
    # Define example peers and pieces (replace with actual data)
    example_peers = [
        {"ip": "127.0.0.1", "port": 6883},
        {"ip": "127.0.0.1", "port": 6882}
    ]
    example_pieces = [0, 1, 2, 3]

    start_download(example_peers, example_pieces)
