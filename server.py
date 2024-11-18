from flask import Flask, jsonify, request
import json

app = Flask(__name__)

def load_metadata():
    try:
        with open('metadata.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"files": []}

@app.route('/get_file_info', methods=['GET'])
def get_file_info():
    file_hash = request.args.get('hash')
    metadata = load_metadata()

    file_entry = next((f for f in metadata["files"] if f["hash"] == file_hash), None)
    if not file_entry:
        return jsonify({"error": "File not found"}), 404

    return jsonify(file_entry)

if __name__ == "__main__":
    app.run(port=5000)
