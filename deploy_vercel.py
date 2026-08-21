#!/usr/bin/env python3
"""
Deploy to Vercel - upload files via POST /v2/files, then create deployment.
"""

import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

VERCEL_TOKEN = os.environ.get("VERCEL_TOKEN", "")
PROJECT_ID = os.environ.get("VERCEL_PROJECT_ID", "")
PUBLISH_DIR = Path(__file__).parent / "output"


def api_call(endpoint, method="GET", data=None, content_type=None):
    url = f"https://api.vercel.com{endpoint}"
    headers = {
        "Authorization": f"Bearer {VERCEL_TOKEN}",
        "User-Agent": "OnzeNews-Deploy/1.0",
    }
    if content_type:
        headers["Content-Type"] = content_type

    if isinstance(data, bytes):
        body = data
    elif data is not None:
        body = json.dumps(data).encode("utf-8")
    else:
        body = None

    req = Request(url, headers=headers, data=body, method=method)
    try:
        with urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {"status": "ok"}
    except HTTPError as e:
        body_text = e.read().decode("utf-8", errors="ignore")
        print(f"API Error {e.code}: {body_text[:300]}")
        raise


def sha1_of_file(filepath):
    h = hashlib.sha1()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if not VERCEL_TOKEN:
        print("ERROR: VERCEL_TOKEN not set")
        sys.exit(1)
    if not PROJECT_ID:
        print("ERROR: VERCEL_PROJECT_ID not set")
        sys.exit(1)

    print(f"Deploying to Vercel project: {PROJECT_ID}")

    # Collect files
    files = {}
    for root, dirs, filenames in os.walk(PUBLISH_DIR):
        for filename in filenames:
            filepath = Path(root) / filename
            if filename in ("vercel.json", ".vercel", ".gitignore"):
                continue
            arcname = str(filepath.relative_to(PUBLISH_DIR)).replace("\\", "/")
            files[arcname] = filepath

    print(f"Files: {len(files)}")

    # Step 1: Upload all files
    print("\nUploading files...")
    uploaded = 0
    failed = 0
    for name in sorted(files.keys()):
        filepath = files[name]
        sha = sha1_of_file(filepath)
        with open(filepath, "rb") as f:
            content = f.read()
        
        try:
            # Try POST with file hash in body
            result = api_call(
                "/v2/files",
                method="POST",
                data=content,
                content_type="application/octet-stream",
            )
            print(f"  Uploaded: {name}")
            uploaded += 1
        except Exception as e:
            print(f"  SKIP: {name} ({e})")
            failed += 1

    print(f"\nUploaded: {uploaded}, Failed: {failed}")

    # Step 2: Create deployment
    print("\nCreating deployment...")
    file_list = []
    for name in sorted(files.keys()):
        sha = sha1_of_file(files[name])
        file_list.append({"file": name, "sha": sha})

    deploy_data = {
        "name": "onzenews-public",
        "files": file_list,
        "projectSettings": {
            "outputDirectory": ".",
            "buildCommand": "",
        },
        "target": "production",
    }

    deploy = api_call(
        "/v13/deployments",
        method="POST",
        data=deploy_data,
        content_type="application/json",
    )

    deploy_id = deploy.get("id", "")
    url = deploy.get("url", "")
    state = deploy.get("readyState", deploy.get("state", "unknown"))
    print(f"Deploy ID: {deploy_id}")
    print(f"State: {state}")
    print(f"URL: https://{url}")
    print(f"\nSite URL: https://onzenews-public.vercel.app")
    return 0


if __name__ == "__main__":
    sys.exit(main())
