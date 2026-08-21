#!/usr/bin/env python3
"""
Deploy to Netlify using the v3 API directly.
No external dependencies needed - uses only stdlib.
"""

import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

AUTH_TOKEN = os.environ.get("NETLIFY_AUTH_TOKEN", "")
SITE_ID = os.environ.get("NETLIFY_SITE_ID", "")
PUBLISH_DIR = Path(__file__).parent / "output"

def api_call(endpoint, method="GET", data=None, content_type=None):
    """Call Netlify API."""
    url = f"https://api.netlify.com/api/v1{endpoint}"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "User-Agent": "OnzeNews-Deploy/1.0",
    }
    if content_type:
        headers["Content-Type"] = content_type
    
    body = json.dumps(data).encode("utf-8") if data else None
    
    req = Request(url, headers=headers, data=body, method=method)
    try:
        with urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {"status": "ok"}
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"API Error {e.code}: {body[:500]}")
        raise


def sha1_of_file(filepath):
    """Compute SHA1 hash of a file."""
    h = hashlib.sha1()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_files(publish_dir):
    """Collect all files in publish dir with their SHA1 hashes."""
    files = {}
    for root, dirs, filenames in os.walk(publish_dir):
        for filename in filenames:
            filepath = Path(root) / filename
            rel = str(filepath.relative_to(publish_dir)).replace("\\", "/")
            files[rel] = sha1_of_file(filepath)
    return files


def main():
    if not AUTH_TOKEN:
        print("ERROR: NETLIFY_AUTH_TOKEN not set")
        sys.exit(1)
    if not SITE_ID:
        print("ERROR: NETLIFY_SITE_ID not set")
        sys.exit(1)
    
    print(f"Deploying to Netlify site: {SITE_ID}")
    print(f"Publish dir: {PUBLISH_DIR}")
    
    # Collect files
    files = collect_files(PUBLISH_DIR)
    print(f"Files to deploy: {len(files)}")
    for f, h in files.items():
        print(f"  {f} -> {h}")
    
    # Create deploy
    print("\nCreating deploy...")
    deploy_data = {
        "files": files,
        "branch": "master",
        "commit_ref": "auto-deploy",
    }
    
    deploy = api_call(
        f"/sites/{SITE_ID}/deploys",
        method="POST",
        data=deploy_data,
        content_type="application/json",
    )
    
    deploy_id = deploy.get("id", "")
    print(f"Deploy ID: {deploy_id}")
    print(f"Deploy URL: {deploy.get('ssl_url', deploy.get('url', 'N/A'))}")
    
    # Check for required uploads
    required = deploy.get("required", [])
    if required:
        print(f"\nUploading {len(required)} files...")
        for item in required:
            path = item.get("path", "")
            sha = item.get("checksum", "")
            print(f"  Uploading {path}...")
            
            # Read file content
            filepath = PUBLISH_DIR / path
            if not filepath.exists():
                print(f"  WARNING: {filepath} not found, skipping")
                continue
            
            with open(filepath, "rb") as f:
                content = f.read()
            
            result = api_call(
                f"/deploys/{deploy_id}/files/{path}",
                method="PUT",
                data=content,
                content_type="application/octet-stream",
            )
            print(f"  OK: {path}")
    else:
        print("\nNo files need uploading (all already exist on CDN)")
    
    # Final status
    print(f"\nDeploy complete!")
    print(f"Site URL: https://onzenews-public.netlify.app")
    return 0


if __name__ == "__main__":
    sys.exit(main())
