import git
import os
import re
import concurrent.futures
import chardet
import chardet
import json
import shutil



def delete_directory(repo_clone_path):
    try:
        shutil.rmtree(repo_clone_path)
        print(f"Successfully deleted directory: {repo_clone_path}")
    except Exception as e:
        print(f"Error deleting directory {repo_clone_path}: {e}")


def get_reponame(repo_url):
    repo_url = repo_url.rstrip('/')
    
    parts = repo_url.split('/')
    username = parts[3]
    reponame = parts[4]

    # Check if the URL contains a branch
    if len(parts) > 5 and parts[5] == 'tree':
        branchname = parts[6]
        combined_string = f"{username}+{reponame}+{branchname}"
    else:
        combined_string = f"{username}+{reponame}"

    return combined_string



def clone_github_repo(repo_url, clone_path):
    try:
        repo_url = repo_url.rstrip('/')

        pattern = re.compile(r'^https://github\.com/([^/]+)/([^/]+)(/tree/([^/]+))?$')
        match = pattern.match(repo_url)

        if not match:
            raise ValueError("Invalid GitHub repository URL")

        username, reponame, _, branchname = match.groups()

        base_repo_url = f"https://github.com/{username}/{reponame}.git"
        if not os.path.exists(clone_path):
            os.makedirs(clone_path)

        if branchname:
            git.Repo.clone_from(base_repo_url, clone_path, branch=branchname)
        else:
            git.Repo.clone_from(base_repo_url, clone_path)
        
        print(f"Repository cloned to {clone_path}")
    except Exception as e:
        print(f"Failed to clone repository: {e}")


def is_valid_repolink(repolink):
    pattern = re.compile(r'^https://github\.com/[^/]+/[^/]+(/tree/[^/]+)?$')
    return bool(pattern.match(repolink))

def process_file(file_path, clone_path):
    relative_path = os.path.relpath(file_path, clone_path)
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            if file_path.endswith('.ipynb'):
                # Handle Jupyter notebook files
                try:
                    content = json.loads(raw_data)
                    cell_sources = [
                        ''.join(cell.get('source', ''))
                        for cell in content.get('cells', [])
                        if cell.get('cell_type') in ('markdown', 'code')
                    ]
                    text = '\n'.join(cell_sources)
                    return relative_path, text
                except json.JSONDecodeError as e:
                    print(f"Failed to parse notebook {file_path}: {e}")
                    return None
            else:
                # Handle other text files
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                if encoding is not None:
                    text = raw_data.decode(encoding)
                    return relative_path, text
                else:
                    print(f"Skipping non-text file: {file_path}")
                    return None
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return None

def create_file_content_dict(clone_path):
    print('Processing Files')
    file_content_dict = {}
    files_to_process = []

    for root, _, files in os.walk(clone_path):
        if '/.git' in root:
            continue
        for file in files:
            file_path = os.path.join(root, file)
            files_to_process.append(file_path)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(process_file, file_path, clone_path): file_path for file_path in files_to_process}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result is not None:
                relative_path, text = result
                file_content_dict[relative_path] = text

    print(f"Processed {len(file_content_dict)} files.")
    return file_content_dict
