#!/usr/bin/env python3
"""
update_gallery.py
-----------------
Cross-platform script (macOS / Linux / Windows) that:
  1. Scans every subdirectory inside ./pic/
  2. Collects image files (jpg, jpeg, png, gif, webp, avif) — case-insensitive
  3. Skips hidden files and system files (.DS_Store, Thumbs.db, etc.)
  4. Rebuilds  pic/groups.json
  5. Updates the inline fallback JSON in index_v3.html
     (the <script type="application/json" id="groupsFallback"> block)

Usage:
  python update_gallery.py              # run from project root
  python update_gallery.py --pic ./pic  # explicit pic folder
  python update_gallery.py --html mypage.html  # explicit html file

Run on macOS/Linux:  python3 update_gallery.py
Run on Windows:      python  update_gallery.py
"""

import argparse
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".bmp", ".tif", ".tiff"}
SKIP_FILES       = {".ds_store", "thumbs.db", "desktop.ini", "groups.json"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_image(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in IMAGE_EXTENSIONS and filename.lower() not in SKIP_FILES


def scan_pic_folder(pic_dir: str) -> list:
    """Return a list of group dicts sorted by folder name."""
    groups = []
    if not os.path.isdir(pic_dir):
        sys.exit(f"ERROR: pic folder not found: {pic_dir}")

    # Only immediate subdirectories become groups (non-recursive)
    for entry in sorted(os.scandir(pic_dir), key=lambda e: e.name.lower()):
        if not entry.is_dir():
            continue
        name = entry.name
        if name.startswith("."):          # skip hidden dirs
            continue

        # Rename any non-lowercase files in-place before collecting
        for f in os.scandir(entry.path):
            if f.is_file() and is_image(f.name) and not f.name.startswith("."):
                lower = f.name.lower()
                if f.name != lower:
                    import uuid as _uuid
                    tmp = os.path.join(entry.path, _uuid.uuid4().hex + "_tmp_" + lower)
                    dst = os.path.join(entry.path, lower)
                    os.rename(f.path, tmp)
                    os.rename(tmp, dst)
                    print(f"    Auto-renamed: {f.name} → {lower}")

        images = sorted(
            [f.name for f in os.scandir(entry.path)
             if f.is_file() and is_image(f.name) and not f.name.startswith(".")],
            key=lambda s: s.lower()
        )
        groups.append({"name": name, "images": images})
        print(f"  [{name}]  →  {len(images)} image(s)")

    return groups


def write_json(path: str, groups: list) -> None:
    data = {"groups": groups}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓  Wrote {path}")


def update_html_fallback(html_path: str, groups: list) -> None:
    """Replace the content of <script type="application/json" id="groupsFallback"> in-place."""
    if not os.path.isfile(html_path):
        print(f"⚠  HTML file not found, skipping: {html_path}")
        return

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Build compact JSON (single line, as it was before)
    new_json = json.dumps({"groups": groups}, ensure_ascii=False, separators=(",", ":"))

    pattern = (
        r'(<script\s+type="application/json"\s+id="groupsFallback"\s*>)'
        r'[\s\S]*?'
        r'(</script>)'
    )
    replacement = r'\g<1>' + new_json + r'\g<2>'

    new_content, n = re.subn(pattern, replacement, content, count=1)
    if n == 0:
        print("⚠  Could not find <script id=\"groupsFallback\"> in the HTML. Fallback not updated.")
        return

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"✓  Updated inline fallback JSON in {html_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Rebuild gallery JSON from pic/ subfolders.")
    parser.add_argument("--pic",  default="pic",           help="Path to the pic folder (default: ./pic)")
    parser.add_argument("--html", default="index_v3.html", help="Path to the HTML file   (default: ./index_v3.html)")
    args = parser.parse_args()

    # Resolve paths relative to this script's directory
    base = os.path.dirname(os.path.abspath(__file__))
    pic_dir   = os.path.join(base, args.pic)
    html_path = os.path.join(base, args.html)
    json_path = os.path.join(pic_dir, "groups.json")

    print(f"\n📂  Scanning subfolders in: {pic_dir}\n")
    groups = scan_pic_folder(pic_dir)

    print()
    write_json(json_path, groups)
    update_html_fallback(html_path, groups)

    print(f"\n✅  Done — {len(groups)} group(s) written.\n")


if __name__ == "__main__":
    main()
