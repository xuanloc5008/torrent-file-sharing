import requests

TRACKER_URL = "https://e825-2001-ee0-4f98-87b0-ec4f-d0bc-297b-2623.ngrok-free.app/announce"
PEER_PORT = 5504

def register_peer():
    print("Please enter your IP: ")
    peer_ip = str(input())
    data = {
        "ip":peer_ip,
        "port": PEER_PORT,
        "files": []  
    }

    try:
        response = requests.post(TRACKER_URL, json=data)
        response.raise_for_status()
        print("Registered with tracker successfully:", response.json())
    except requests.HTTPError as e:
        print(f"HTTP error during tracker registration: {e}")
        print(f"Response content: {e.response.text}")
    except requests.RequestException as e:
        print(f"Error communicating with tracker: {e}")

if __name__ == "__main__":
    register_peer()
