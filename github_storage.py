import os
import base64
from github import Github
import json

# GitHub configuration
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
REPO_NAME = os.environ.get('GITHUB_REPO', 'your-username/your-repo')
FILE_PATH = 'protected_numbers.json'

def load_protected_numbers():
    """
    Load protected numbers from GitHub repository
    """
    protected_numbers = set()
    
    try:
        if not GITHUB_TOKEN:
            print("⚠️  GITHUB_TOKEN not set, using local storage only")
            return protected_numbers
            
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        
        try:
            file_content = repo.get_contents(FILE_PATH)
            content = base64.b64decode(file_content.content).decode('utf-8')
            numbers_list = json.loads(content)
            protected_numbers = set(numbers_list)
            print(f"✅ Loaded {len(protected_numbers)} protected numbers from GitHub")
            
        except Exception as e:
            print(f"⚠️  No existing protected numbers file found, creating new one: {e}")
            # Create initial file
            initial_content = json.dumps([])
            repo.create_file(FILE_PATH, "Initial protected numbers file", initial_content)
            print("✅ Created new protected numbers file on GitHub")
            
    except Exception as e:
        print(f"❌ Error loading from GitHub: {e}")
        print("⚠️  Falling back to local storage")
        
    return protected_numbers

def save_protected_numbers(protected_numbers):
    """
    Save protected numbers to GitHub repository
    """
    try:
        if not GITHUB_TOKEN:
            print("⚠️  GITHUB_TOKEN not set, cannot save to GitHub")
            return False
            
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        
        # Convert set to list for JSON serialization
        numbers_list = list(protected_numbers)
        content = json.dumps(numbers_list, indent=2)
        
        try:
            # Try to get existing file
            file_content = repo.get_contents(FILE_PATH)
            # Update existing file
            repo.update_file(FILE_PATH, f"Update protected numbers - {len(protected_numbers)} numbers", content, file_content.sha)
            print(f"✅ Updated protected numbers on GitHub: {len(protected_numbers)} numbers")
            
        except Exception as e:
            # File doesn't exist, create new one
            repo.create_file(FILE_PATH, f"Create protected numbers - {len(protected_numbers)} numbers", content)
            print(f"✅ Created protected numbers file on GitHub: {len(protected_numbers)} numbers")
            
        return True
        
    except Exception as e:
        print(f"❌ Error saving to GitHub: {e}")
        return False

# Alternative simple file-based storage (fallback)
def load_protected_numbers_local():
    """
    Load protected numbers from local file (fallback)
    """
    protected_numbers = set()
    try:
        if os.path.exists('protected_numbers.json'):
            with open('protected_numbers.json', 'r') as f:
                numbers_list = json.load(f)
                protected_numbers = set(numbers_list)
            print(f"✅ Loaded {len(protected_numbers)} protected numbers from local file")
    except Exception as e:
        print(f"❌ Error loading from local file: {e}")
    return protected_numbers

def save_protected_numbers_local(protected_numbers):
    """
    Save protected numbers to local file (fallback)
    """
    try:
        numbers_list = list(protected_numbers)
        with open('protected_numbers.json', 'w') as f:
            json.dump(numbers_list, f, indent=2)
        print(f"✅ Saved {len(protected_numbers)} protected numbers to local file")
        return True
    except Exception as e:
        print(f"❌ Error saving to local file: {e}")
        return False
