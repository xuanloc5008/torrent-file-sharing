import os
import socket
import threading
import requests

SERVER_URL = 'http://127.0.0.1:5000'
PEER_PORT = 6500
SHARED_FILES_DIR = 'shared_files'

def start_peer_server(peer_port):
    def handle_client(client_socket):
        try:
            request = client_socket.recv(1024).decode()
            file_name, chunk_index = request.split(",")
            chunk_index = int(chunk_index)

            file_path = os.path.join(SHARED_FILES_DIR, file_name)
            with open(file_path, 'r') as f:
                chunks = f.readlines()  
                chunk_data = chunks[chunk_index].strip()

            client_socket.send(chunk_data.encode())
        except Exception as e:
            print(f"Error serving chunk: {e}")
        finally:
            client_socket.close()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", peer_port))
    server.listen(5)
    print(f"Peer server running on port {peer_port}...")

    while True:
        client_socket, addr = server.accept()
        threading.Thread(target=handle_client, args=(client_socket,)).start()

def request_chunk(peer_ip, peer_port, file_name, chunk_index):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((peer_ip, peer_port))
        client.send(f"{file_name},{chunk_index}".encode())
        chunk_data = client.recv(1024).decode()
        return chunk_data
    except Exception as e:
        print(f"Error requesting chunk: {e}")
        return None
    finally:
        client.close()

def download_file(file_info):
    file_data = file_info['data']
    file_name = file_data['file_name']
    file_size = file_data['file_size']
    info_hash = file_data['info_hash']
    peer_ip = file_data['peer_address']
    peer_port = file_data['peer_port']  

    print(f"Downloading file: {file_name} ({file_size} bytes)")

    num_chunks = 4 
    downloaded_chunks = []

    for chunk_index in range(num_chunks):
        print(f"Requesting chunk {chunk_index} from {peer_port}...")
        chunk_data = request_chunk(peer_ip, peer_port, file_name, chunk_index)
        if chunk_data:
            downloaded_chunks.append(chunk_data)
        else:
            print(f"Failed to retrieve chunk {chunk_index} from {peer_port}")

    os.makedirs(SHARED_FILES_DIR, exist_ok=True)
    with open(os.path.join(SHARED_FILES_DIR, file_name), 'w') as f:
        f.write("\n".join(downloaded_chunks))

    print(f"File '{file_name}' downloaded successfully and saved.")

def get_file_info(file_hash):
    response = requests.get(f"{SERVER_URL}/file/fetch", params={"info_hash": file_hash})
    if response.status_code == 404:
        print("File not found on server.")
        return None
    return response.json()

def announce_peer(info_hash):
    peer_address = f"{socket.gethostbyname(socket.gethostname())}:{PEER_PORT}"
    payload = {"info_hash": info_hash, "peer_address": peer_address, "peer_port": PEER_PORT}
    response = requests.post(f"{SERVER_URL}/file/peers/announce", json=payload)
    if response.status_code == 201:
        print(f"Peer announced successfully for file: {info_hash}")
    else:
        print(f"Failed to announce peer: {response.json()}")

if __name__ == "__main__":
    threading.Thread(target=start_peer_server, args=(PEER_PORT,), daemon=True).start()

    example_hash = input("Enter file hash to download: ")

    announce_peer(example_hash)

    file_info = get_file_info(example_hash)
    if file_info:
        download_file(file_info)
