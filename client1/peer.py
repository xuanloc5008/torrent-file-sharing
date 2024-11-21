import os
import socket
import threading
import requests

SERVER_URL = 'http://127.0.0.1:5000'
PEER_PORT = 6000
SHARED_FILES_DIR = '/Users/xuanloc/Documents/GitHub/torrent-file-sharing/client1/shared_files'

download_threads = []
downloaded_chunks = {}

chunk_size = 1024  

def start_peer_server(peer_port):
    def handle_client(client_socket):
        request = client_socket.recv(1024).decode()
        file_name, chunk_index = request.split(",")
        chunk_index = int(chunk_index)
        file_path = os.path.join(SHARED_FILES_DIR, file_name)
        try:
            with open(file_path, 'r') as f:
                chunks = f.readlines()
                chunk_data = chunks[chunk_index].strip()
            client_socket.send(chunk_data.encode())
        except Exception as e:
            print(f"Error: {e}")
        finally:
            client_socket.close()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", peer_port))
    server.listen(5)
    print(f"Peer server running on port {peer_port}...")

    while True:
        client_socket, addr = server.accept()
        threading.Thread(target=handle_client, args=(client_socket,)).start()

def upload_file_to_server(file_name, file_size):
    peer_address = socket.gethostbyname(socket.gethostname())
    peer_port = PEER_PORT
    payload = {
        "file_name": file_name,
        "file_size": file_size,
        "peer_address": peer_address,
        "peer_port": peer_port
    }
    response = requests.post(f"{SERVER_URL}/file/publish", json=payload)
    if response.status_code == 201:
        print(f"File '{file_name}' published successfully.")
    else:
        print(f"Failed to publish file: {response.json()}")

def split_file(file_path):
    chunks = []

    with open(file_path, 'r') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            chunks.append(chunk.strip())

    return chunks

def upload_and_split(file_name):
    file_path = os.path.join(SHARED_FILES_DIR, file_name)
    if not os.path.exists(file_path):
        print("File not found in shared directory.")
        return

    file_size = os.path.getsize(file_path)
    chunks = split_file(file_path)

    with open(file_path, 'w') as f:
        for chunk in chunks:
            f.write(chunk + '\n')

    upload_file_to_server(file_name, file_size)

def download_chunk(peer_ip, peer_port, file_name, chunk_index):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((peer_ip, peer_port))
        request = f"{file_name},{chunk_index}"
        client.send(request.encode())

        chunk_data = client.recv(1024).decode()
        client.close()

        if chunk_data:
            print(f"Downloaded chunk {chunk_index}: {chunk_data}")
            downloaded_chunks[chunk_index] = chunk_data
        else:
            print(f"Failed to download chunk {chunk_index}.")
    except Exception as e:
        print(f"Error downloading chunk {chunk_index}: {e}")

def download_file(info_hash):
    print(f"Downloading file with info_hash: {info_hash}...")

    response = requests.get(f"{SERVER_URL}/file/fetch", params={"info_hash": info_hash})
    if response.status_code != 200:
        print(f"Error fetching file info for info_hash {info_hash}: {response.json()}")
        return

    data = response.json()
    file_info = data['file']
    file_name = file_info['file_name']
    file_size = file_info['file_size']  
    num_chunks = (file_size // chunk_size) + (1 if file_size % chunk_size else 0)
    response = requests.get(f"{SERVER_URL}/file/peers", params={"info_hash": info_hash})
    if response.status_code != 200:
        print(f"Error fetching peers for info_hash {info_hash}: {response.json()}")
        return

    peers = response.json().get('peers', [])
    if not peers:
        print(f"No peers available for {file_name}.")
        return
    chunk_data = []
    i = 0
    for chunk_index in range(num_chunks):
        peer = peers[chunk_index % len(peers)] 
        peer_ip = peer['peer_address']
        peer_port = peer['peer_port']
        # download_chunk(peer_ip=peer_ip, peer_port=peer_port, file_name=file_name, chunk_index=chunk_index)
        thread = threading.Thread(target=download_chunk, args=(peer_ip, peer_port, file_name, chunk_index))
        download_threads.append(thread)
        thread.start()

    for thread in download_threads:
        thread.join()

    print(f"Combining chunks into file: {file_name}")
    with open(os.path.join(SHARED_FILES_DIR, file_name), 'w') as f:
        for chunk_index in range(num_chunks):
            chunk_data = downloaded_chunks.get(chunk_index)
            if chunk_data:
                f.write(chunk_data + '\n')

    print(f"File {file_name} download complete.")

if __name__ == "__main__":
    threading.Thread(target=start_peer_server, args=(PEER_PORT,), daemon=True).start()

    print("Peer-to-peer file-sharing program started.")
    
    try:
        while True:
            print("\nSelect one of these options:")
            print("1. Publish file (upload to server and announce chunks)")
            print("2. Download file")
            print("3. Seed a file")
            print("4. Quit")

            choice = input("Enter your choice: ").strip().lower()
            if choice in ["1", "publish"]:
                file_name = input("Enter the file name to publish: ").strip()
                upload_and_split(file_name)

            elif choice in ["2", "download"]:
                info_hash = input("Enter the file info_hash to download: ").strip()
                download_file(info_hash)

            elif choice in ["3", "seed"]:
                info_hash = input("Enter the info_hash of the file to seed: ").strip()
                payload = {"info_hash": info_hash, "peer_address": socket.gethostbyname(socket.gethostname()), "peer_port": PEER_PORT}
                response = requests.post(f"{SERVER_URL}/file/peers/announce", json=payload)
                if response.status_code == 201:
                    print("Seeding started successfully.")
                else:
                    print(f"Failed to seed the file: {response.json()}")

            elif choice in ["4", "quit", "exit"]:
                print("Exiting program. Goodbye!")
                break

            else:
                print("Invalid choice. Please try again.")
    
    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting gracefully.")
