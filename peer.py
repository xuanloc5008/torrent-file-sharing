import os
import socket
import threading
import requests

SERVER_URL = 'http://127.0.0.1:5000'
PEER_PORT = 6000
SHARED_FILES_DIR = 'shared_files'

def start_peer_server(peer_port):
    def handle_client(client_socket):
        request = client_socket.recv(1024).decode()
        file_name, chunk_index = request.split(",")
        chunk_index = int(chunk_index)

        file_path = os.path.join(SHARED_FILES_DIR, file_name)
        with open(file_path, 'r') as f:
            chunks = f.readlines()  
            chunk_data = chunks[chunk_index].strip()

        client_socket.send(chunk_data.encode())
        client_socket.close()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", peer_port))
    server.listen(5)
    print(f"Peer server running on port {peer_port}...")

    while True:
        client_socket, addr = server.accept()
        threading.Thread(target=handle_client, args=(client_socket,)).start()

def request_chunk(peer_ip, peer_port, file_name, chunk_index):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((peer_ip, peer_port))

    client.send(f"{file_name},{chunk_index}".encode())

    chunk_data = client.recv(1024).decode()
    client.close()
    return chunk_data

def download_file(file_info):
    file_name = file_info['name']
    peers = file_info['peers']
    file_size = file_info['size']
    num_chunks = 4  # Assume file is split into 4 chunks

    print(f"Downloading file: {file_name} ({file_size} bytes)")

    downloaded_chunks = []
    for chunk_index in range(num_chunks):
        peer = peers[chunk_index % len(peers)]  
        peer_ip, peer_port = peer.split(":")
        peer_port = int(peer_port)

        print(f"Requesting chunk {chunk_index} from {peer}...")
        chunk_data = request_chunk(peer_ip, peer_port, file_name, chunk_index)
        downloaded_chunks.append(chunk_data)
    print(downloaded_chunks)
    # os.makedirs(SHARED_FILES_DIR, exist_ok=True)
    # with open(f"{SHARED_FILES_DIR}/{file_name}", 'w') as f:
    #     f.write("\n".join(downloaded_chunks))

    print(f"File '{file_name}' downloaded successfully and saved.")

def get_file_info(file_hash):
    response = requests.get(f"{SERVER_URL}/get_file_info", params={"hash": file_hash})
    if response.status_code == 404:
        print("File not found on server.")
        return None
    return response.json()

if __name__ == "__main__":
    threading.Thread(target=start_peer_server, args=(PEER_PORT,)).start()

    example_hash = input("Enter file hash to download: ")
    file_info = get_file_info(example_hash)
    if file_info:
        download_file(file_info)
