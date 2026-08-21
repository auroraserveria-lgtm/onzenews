#!/usr/bin/env python3
"""
Deploy to Vercel using the v13 API - file-based deployment.
"""

import hashlib
import json
import os
import sys
import zipfile
import tempfile
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

VERCEL_TOKEN = os.environ.get("VERCEL_TOKEN", "")
SITE_ID = os.environ.get("VERCEL_PROJECT_ID", "")
PUBLISH_DIR = Path(__file__).parent / "output"


def api_call(endpoint, method="GET", data=None, content_type=None):
    """Call Vercel API."""
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
        print(f"API Error {e.code}: {body_text[:500]}")
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
    if not SITE_ID:
        print("ERROR: VERCEL_PROJECT_ID not set")
        sys.exit(1)

    print(f"Deploying to Vercel project: {SITE_ID}")
    print(f"Publish dir: {PUBLISH_DIR}")

    # Collect files
    files = {}
    file_hashes = {}
    for root, dirs, filenames in os.walk(PUBLISH_DIR):
        for filename in filenames:
            filepath = Path(root) / filename
            if filename in ("vercel.json", ".vercel"):
                continue
            arcname = str(filepath.relative_to(PUBLISH_DIR)).replace("\\", "/")
            files[arcname] = filepath
            file_hashes[arcname] = sha1_of_file(filepath)

    print(f"Files: {len(files)}")
    for f in sorted(files.keys()):
        print(f"  {f}")

    # Create deployment with file digests
    print("\nCreating deployment...")
    deploy_data = {
        "name": "onzenews-public",
        "files": [{"file": name, "sha": sha} for name, sha in file_hashes.items()],
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
    state = deploy.get("readyState", "unknown")
    print(f"Deploy ID: {deploy_id}")
    print(f"State: {state}")
    print(f"URL: https://{url}")

    # Check for missing files
    missing = deploy.get("missing", [])
    if missing:
        print(f"\nUploading {len(missing)} missing files...")
        for item in missing:
            name = item.get("file", "")
            sha = item.get("sha1", item.get("sha", ""))
            filepath = files.get(name)
            if not filepath:
                print(f"  WARNING: {name} not found")
                continue

            print(f"  Uploading {name}...")
            with open(filepath, "rb") as f:
                content = f.read()

            try:
                upload_url = f"/v2/files/{sha}"
                api_call(upload_url, method="PUT", data=content, content_type="application/octet-stream")
                print(f"  OK: {name}")
            except Exception as e:
                print(f"  FAILED: {name} - {e}")
    else:
        print("\nNo missing files (all exist on CDN)")

    print(f"\nDeploy complete!")
    print(f"Site URL: https://onzenews-public.vercel.app")
    return 0


if __name__ == "__main__":
    sys.exit(main())
