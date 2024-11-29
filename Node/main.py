import requests

TRACKER_URL = "http://localhost:5500/announce"
PEER_PORT = 5501

def register_peer():
    data = {
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
