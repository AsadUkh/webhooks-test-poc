import os
import subprocess
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', 'dfksigw5f')
API_KEY = os.getenv('CLOUDINARY_API_KEY', '272356752637981')
API_SECRET = os.getenv('CLOUDINARY_API_SECRET', '672xGcI9hd6fBdlw5h2TyRVgD14')
UPLOAD_PRESET = 'ml_default'

def get_modified_files():
    modified_files = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD^', 'HEAD'], text=True).splitlines()
    new_files = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], text=True).splitlines()
    all_files = modified_files + new_files
    filtered_files = [f for f in all_files if not (f.startswith('node_modules/') or f.startswith('.git/'))]
    return filtered_files

def upload_file_to_cloudinary(file_path):
    with open(file_path, 'rb') as file:
        upload_url = f'https://api.cloudinary.com/v1_1/{CLOUD_NAME}/raw/upload'
        files = {'file': file}
        data = {
            'upload_preset': UPLOAD_PRESET,
            'public_id': file_path,
        }
        response = requests.post(upload_url, data=data, files=files, auth=(API_KEY, API_SECRET))
        if response.status_code == 200:
            print(f'Successfully uploaded: {file_path}')
        else:
            print(f'Failed to upload {file_path}. Error: {response.text}')

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    try:
        # Verify that it's a valid GitHub webhook (optional but recommended)
        if request.headers.get('X-GitHub-Event') is None:
            return jsonify({'error': 'Invalid GitHub webhook event'}), 400

        print("Received GitHub webhook event...")

        # Handle the GitHub webhook event (e.g., on push or pull request)
        payload = request.json

        # Check if it's a push event and only proceed if there are modified files
        if payload.get('ref') == 'refs/heads/main':  # Ensure it's a push to the main branch
            print(f"Processing push event to the main branch")

            # Get the list of changed files
            changed_files = get_modified_files()
            if not changed_files:
                return jsonify({'message': 'No modified files found to upload'}), 200

            print(f'Files to upload: {changed_files}')

            # Upload the files to Cloudinary
            for file_path in changed_files:
                if os.path.isfile(file_path):
                    upload_file_to_cloudinary(file_path)
                else:
                    print(f'No valid file found for: {file_path}')

            return jsonify({'message': 'Files uploaded successfully'}), 200
        else:
            return jsonify({'error': 'Not a push to main branch'}), 400

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'An error occurred'}), 500


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
