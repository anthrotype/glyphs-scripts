#MenuTitle: Download latest fontmake
# Copyright 2023 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__doc__ = """Download latest fontmake

This script downloads the latest fontmake's standalone zip-app (.pyz) from
Github Releases and unpacks it to the same directory as this script.
The app is built for macOS and Python 3.11, and works with both x86_64 (Intel)
and arm64 (Apple Silicon) architectures.
"""

import os
import http.client
import json
import urllib.parse
import urllib.request
import zipfile
import shutil
from pathlib import Path


GITHUB_API_URL = "https://api.github.com/repos/googlefonts/fontmake"
FONTMAKE_ZIP = "fontmake-{version}-cp311-cp311-macosx_11_0_universal2.zip"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    # "Authorization": f"token {os.environ.get("GITHUB_ACCESS_TOKEN")}"
}
HERE = Path(__file__).parent.resolve()


def get_redirected_url(url):
    url_parts = urllib.parse.urlsplit(url)
    conn = http.client.HTTPSConnection(url_parts.netloc)
    conn.request("HEAD", url_parts.path, headers=HEADERS)
    response = conn.getresponse()
    conn.close()

    if response.status in (301, 302, 303, 307):
        new_location = response.getheader("Location")
        # Recursively follow the redirection
        return get_redirected_url(new_location)
    else:
        return url


def get_latest_release_tag():
    url_parts = urllib.parse.urlsplit(GITHUB_API_URL + "/releases/latest")
    conn = http.client.HTTPSConnection(url_parts.netloc)
    conn.request("GET", url_parts.path, headers=HEADERS)
    response = conn.getresponse()
    if response.status != 200:
        print(f"Failed to fetch the latest release information: {response.status}")
        return None

    data = json.loads(response.read().decode("utf-8"))
    version = data["tag_name"]
    conn.close()

    return version


def download_and_extract_zip(tag_name, output_dir):
    version = tag_name
    if version.startswith("v"):
        version = version[1:]

    zip_filename = FONTMAKE_ZIP.format(version=version)
    zip_path = Path(output_dir) / zip_filename

    url_parts = urllib.parse.urlsplit(GITHUB_API_URL + f"/releases/tags/{tag_name}")
    conn = http.client.HTTPSConnection(url_parts.netloc)
    conn.request("GET", url_parts.path, headers=HEADERS)
    response = conn.getresponse()
    if response.status != 200:
        print(f"Failed to fetch the release assets: {response.status}")
        return

    data = json.loads(response.read().decode("utf-8"))
    assets = data["assets"]
    zip_url = None
    for asset in assets:
        if asset["name"] == zip_filename:
            zip_url = asset["browser_download_url"]
            break

    conn.close()

    if not zip_url:
        print(f"Asset file not found for version {zip_filename}.")
        return

    print(f"Downloading {zip_url}")

    zip_url = get_redirected_url(zip_url)
    try:
        urllib.request.urlretrieve(zip_url, zip_path)
    except urllib.error.HTTPError as e:
        print(f"Failed to download the zip file from {zip_url}: {e}")
        return

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(output_dir)

    extracted_dir = Path(output_dir) / zip_path.stem
    if not extracted_dir.is_dir():
        print(f"Failed to extract the zip file: {zip_path}")
        return

    fontmake_exe = extracted_dir / "fontmake"
    if not fontmake_exe.is_file():
        print(f"Extracted zip does not contain 'fontmake': {extracted_dir}")
        return

    # rename to fontmake-{version}.pyz and move to output_dir
    fontmake_exe.rename(Path(output_dir) / f"fontmake-{version}.pyz")

    print(f"Extracted to {output_dir}")

    shutil.rmtree(extracted_dir, ignore_errors=True)
    zip_path.unlink()


def main():
    latest_tag = get_latest_release_tag()
    if latest_tag is None:
        print("Failed to retrieve the latest release version.")
        return 1

    download_and_extract_zip(latest_tag, HERE)


if __name__ == "__main__":
    main()
