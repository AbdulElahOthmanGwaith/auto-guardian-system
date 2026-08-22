import os
import ipaddress
import re
import socket
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests


_BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain", "metadata.google.internal"}
_MAX_REDIRECTS = 3


def find_links(text):
    # Regex to find URLs
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    links = re.findall(url_pattern, text)
    return [link.rstrip('.,;:!?)]}>') for link in links]


def _is_public_http_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False

    hostname = parsed.hostname.lower().rstrip(".")
    if hostname in _BLOCKED_HOSTNAMES or hostname.endswith(".local"):
        return False

    try:
        addresses = socket.getaddrinfo(hostname, parsed.port, type=socket.SOCK_STREAM)
    except (OSError, ValueError):
        return False

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if any((ip.is_private, ip.is_loopback, ip.is_link_local, ip.is_multicast, ip.is_reserved, ip.is_unspecified)):
            return False
    return True


def check_link(url):
    current_url = url
    try:
        for _ in range(_MAX_REDIRECTS + 1):
            if not _is_public_http_url(current_url):
                return False

            response = requests.head(current_url, timeout=5, allow_redirects=False)
            if 300 <= response.status_code < 400:
                location = response.headers.get("Location")
                if not location:
                    return False
                current_url = urljoin(current_url, location)
                continue
            return response.status_code < 400
    except (requests.RequestException, OSError, ValueError):
        return False

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
