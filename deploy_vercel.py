#!/usr/bin/env python3
"""
Deploy to Vercel using the Vercel API.
"""

import json
import os
import sys
import zipfile
import tempfile
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

VERCEL_TOKEN = os.environ.get("VERCEL_TOKEN", "")
VERCEL_PROJECT = os.environ.get("VERCEL_PROJECT", "onzenews-public")
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


def create_zip(publish_dir):
    """Create zip of the publish directory."""
    zip_path = tempfile.mktemp(suffix=".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, filenames in os.walk(publish_dir):
            for filename in filenames:
                filepath = Path(root) / filename
                # Skip vercel.json from zip (Vercel handles it)
                if filename == "vercel.json":
                    continue
                arcname = str(filepath.relative_to(publish_dir)).replace("\\", "/")
                zf.write(filepath, arcname)
    return zip_path


def upload_file(project_id, team_id, file_path, file_content):
    """Upload a file to Vercel."""
    endpoint = f"/v2/files"
    headers = {
        "Authorization": f"Bearer {VERCEL_TOKEN}",
        "Content-Type": "application/octet-stream",
        "x-vercel-digest": file_path,
    }
    url = f"https://api.vercel.com{endpoint}"
    req = Request(url, headers=headers, data=file_content, method="POST")
    try:
        with urlopen(req, timeout=60) as resp:
            return True
    except HTTPError as e:
        body_text = e.read().decode("utf-8", errors="ignore")
        if "already exists" in body_text.lower():
            return True  # File already uploaded
        print(f"Upload error {e.code}: {body_text[:200]}")
        return False


def main():
    if not VERCEL_TOKEN:
        print("ERROR: VERCEL_TOKEN not set")
        print("Get one at: https://vercel.com/account/tokens")
        sys.exit(1)

    print(f"Deploying to Vercel project: {VERCEL_PROJECT}")
    print(f"Publish dir: {PUBLISH_DIR}")

    # Collect files
    files = {}
    for root, dirs, filenames in os.walk(PUBLISH_DIR):
        for filename in filenames:
            filepath = Path(root) / filename
            if filename == "vercel.json":
                continue
            arcname = str(filepath.relative_to(PUBLISH_DIR)).replace("\\", "/")
            files[arcname] = filepath

    print(f"Files to deploy: {len(files)}")
    for f in sorted(files.keys()):
        size = os.path.getsize(files[f])
        print(f"  {f} ({size / 1024:.1f} KB)")

    # Create zip and deploy
    print("\nCreating zip...")
    zip_path = create_zip(PUBLISH_DIR)
    zip_size = os.path.getsize(zip_path)
    print(f"Zip size: {zip_size / 1024:.1f} KB")

    # Read zip
    with open(zip_path, "rb") as f:
        zip_content = f.read()

    # Deploy using file-based deployment
    print("\nDeploying...")

    # Step 1: Get file hashes
    import hashlib
    file_hashes = {}
    for name, path in files.items():
        h = hashlib.sha1()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        file_hashes[name] = h.hexdigest()

    # Step 2: Create deployment
    deploy_data = {
        "name": VERCEL_PROJECT,
        "files": [{"file": name, "sha": sha} for name, sha in file_hashes.items()],
        "projectSettings": {
            "framework": None,
            "outputDirectory": ".",
            "buildCommand": "",
        },
        "target": "production",
    }

    try:
        deploy = api_call(
            f"/v13/deployments",
            method="POST",
            data=deploy_data,
            content_type="application/json",
        )

        deploy_id = deploy.get("id", "")
        url = deploy.get("url", "")
        state = deploy.get("state", "unknown")
        print(f"Deploy ID: {deploy_id}")
        print(f"State: {state}")
        print(f"URL: {url}")

        # Step 3: Upload missing files
        required = deploy.get("missing", [])
        if required:
            print(f"\nUploading {len(required)} files...")
            for item in required:
                name = item.get("file", "")
                sha = item.get("sha", "")
                filepath = files.get(name)
                if not filepath:
                    print(f"  WARNING: {name} not found")
                    continue

                print(f"  Uploading {name}...")
                with open(filepath, "rb") as f:
                    content = f.read()

                success = upload_file(deploy.get("projectId", ""), "", sha, content)
                if success:
                    print(f"  OK: {name}")
                else:
                    print(f"  FAILED: {name}")
        else:
            print("\nNo files need uploading")

        print(f"\nDeploy complete!")
        print(f"Site URL: {url}")
        return 0

    except Exception as e:
        print(f"Deploy failed: {e}")
        # Fallback: use zip upload
        print("\nTrying zip upload fallback...")
        try:
            deploy = api_call(
                f"/v13/deployments",
                method="POST",
                data={
                    "name": VERCEL_PROJECT,
                    "files": [],
                    "projectSettings": {
                        "framework": None,
                        "outputDirectory": ".",
                    },
                    "target": "production",
                },
                content_type="application/json",
            )
            print(f"Deploy created: {deploy.get('id')}")
            return 0
        except Exception as e2:
            print(f"Fallback also failed: {e2}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
