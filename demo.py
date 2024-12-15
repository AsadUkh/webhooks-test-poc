import os
import requests
import git
import tempfile
import shutil
from flask import Flask, request, jsonify

app = Flask(__name__)

CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', 'your-cloud-name')
API_KEY = os.getenv('CLOUDINARY_API_KEY', 'your-api-key')
API_SECRET = os.getenv('CLOUDINARY_API_SECRET', 'your-api-secret')
UPLOAD_PRESET = 'ml_default'

def clone_repo(repo_url):
    """Clone the repository into a temporary directory."""
    temp_dir = tempfile.mkdtemp()  # Create a temporary directory to clone the repo
    try:
        print(f"Cloning repository {repo_url} into {temp_dir}...")
        repo = git.Repo.clone_from(repo_url, temp_dir)
        return temp_dir, repo
    except Exception as e:
        print(f"Error cloning repository: {e}")
        return None, None

def upload_file_to_cloudinary(file_path, commit_hash):
    """Upload the file to Cloudinary."""
    with open(file_path, 'rb') as file:
        upload_url = f'https://api.cloudinary.com/v1_1/{CLOUD_NAME}/raw/upload'
        files = {'file': file}
        data = {
            'upload_preset': UPLOAD_PRESET,
            'public_id': f"{commit_hash}_{file_path}",  # Unique public ID based on commit
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

        # Extract the repository URL from the payload
        repo_url = payload['repository']['clone_url']
        print(f"Cloning repository from {repo_url}...")

        # Ensure it's a push event and only proceed if there are modified files
        if payload.get('ref') == 'refs/heads/main':  # Ensure it's a push to the main branch
            print(f"Processing push event to the main branch")

            # Clone the repo into a temporary directory
            repo_path, repo = clone_repo(repo_url)
            if not repo_path:
                return jsonify({'error': 'Failed to clone the repository'}), 500

            # Extract the commit details
            commits = payload.get('commits', [])
            if not commits:
                shutil.rmtree(repo_path)  # Clean up the repo directory
                return jsonify({'error': 'No commits in the push event'}), 400

            # Process each commit in the push event
            for commit in commits:
                commit_hash = commit['id']
                commit_message = commit['message']
                print(f"Processing commit {commit_hash}: {commit_message}")

                # Extract the changed files from the commit
                modified_files = commit.get('modified', [])
                added_files = commit.get('added', [])
                removed_files = commit.get('removed', [])

                all_files = modified_files + added_files + removed_files
                filtered_files = [f for f in all_files if not (f.startswith('node_modules/') or f.startswith('.git/'))]

                if not filtered_files:
                    print(f"No valid files in commit {commit_hash} to upload.")
                    continue

                # Upload each file to Cloudinary
                for file_path in filtered_files:
                    # Construct the full path to the file
                    full_file_path = os.path.join(repo_path, file_path)
                    if os.path.isfile(full_file_path):
                        print(f'Uploading {full_file_path} to Cloudinary...')
                        upload_file_to_cloudinary(full_file_path, commit_hash)
                    else:
                        print(f'No valid file found for: {full_file_path}')

            # Clean up the cloned repo directory
            shutil.rmtree(repo_path)

            return jsonify({'message': 'Files uploaded successfully'}), 200
        else:
            return jsonify({'error': 'Not a push to main branch'}), 400

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'An error occurred'}), 500


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
