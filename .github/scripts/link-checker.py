import os
import re
import requests
from pathlib import Path

def find_links(text):
    # Regex to find URLs
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(url_pattern, text)

def check_link(url):
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        return response.status_code < 400
    except:
        return False

def main():
    print("Starting Link Checker...")
    project_root = Path(".")
    files_to_check = list(project_root.glob("**/*.md")) + list(project_root.glob("**/*.html"))
    
    broken_links = []
    for file_path in files_to_check:
        if ".github" in str(file_path) and "scripts" in str(file_path):
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            links = find_links(content)
            for link in links:
                if not check_link(link):
                    broken_links.append((str(file_path), link))
    
    if broken_links:
        print(f"Found {len(broken_links)} broken links:")
        for file, link in broken_links:
            print(f"- {file}: {link}")
    else:
        print("No broken links found!")

if __name__ == "__main__":
    main()
