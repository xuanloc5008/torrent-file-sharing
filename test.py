import socket
server_ip = "172.29.0.1"  
server_port = 12345

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((server_ip, server_port))
print(client_socket.recv(1024).decode())  
client_socket.close()