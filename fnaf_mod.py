"""
FNAF Teacher Mod Tool
=====================
HOW TO USE:
1. Put this script in the same folder as your game files (index.html, main.js, etc.)
2. Run:  python fnaf_mod.py extract
   → Pulls all media into replacements/images/, replacements/gifs/, replacements/audio/
3. Swap out whichever files you want (same filename, auto-resized for images)
4. Run:  python fnaf_mod.py repack
   → Rebuilds the game with your new files
5. Run:  python fnaf_mod.py activate
   → Swaps the modded parts in

To preview all extracted images: python fnaf_mod.py preview
To play the modded game:         python fnaf_mod.py play  →  http://localhost:8000
To back up to GitHub:            python fnaf_mod.py backup
"""

import os, sys, shutil, zipfile, subprocess, datetime, base64
from pathlib import Path

PARTS         = 8
PARTS_PREFIX  = "resources.zip.part"
RESOURCES_ZIP = "resources.zip"
REPLACEMENTS_DIR = "replacements"
MODDED_ZIP    = "resources_modded.zip"

TYPE_FOLDERS = {
    ".png": "images",
    ".jpg": "images",
    ".gif": "gifs",
    ".ogg": "audio",
    ".mp3": "audio",
}
IMAGE_EXTENSIONS = (".png", ".jpg")

def is_media(name):
    return Path(name).suffix.lower() in TYPE_FOLDERS

def is_image(name):
    return Path(name).suffix.lower() in IMAGE_EXTENSIONS

def subfolder_for(name):
    return TYPE_FOLDERS.get(Path(name).suffix.lower())

def extract():
    print("📦 Combining part files...")
    with open(RESOURCES_ZIP, "wb") as out:
        for i in range(1, PARTS + 1):
            part = f"{PARTS_PREFIX}{i}"
            if not os.path.exists(part):
                print(f"  ❌ Missing {part}! Make sure all part files are here.")
                return
            with open(part, "rb") as f:
                out.write(f.read())
            print(f"  ✅ {part}")

    print(f"\n📂 Extracting media to '{REPLACEMENTS_DIR}/' subfolders...")

    for folder in set(TYPE_FOLDERS.values()):
        os.makedirs(os.path.join(REPLACEMENTS_DIR, folder), exist_ok=True)

    counts = {"images": 0, "gifs": 0, "audio": 0}

    with zipfile.ZipFile(RESOURCES_ZIP, "r") as z:
        for name in z.namelist():
            if not is_media(name):
                continue
            folder = subfolder_for(name)
            filename = Path(name).name
            out_path = os.path.join(REPLACEMENTS_DIR, folder, filename)
            with z.open(name) as src, open(out_path, "wb") as dst:
                dst.write(src.read())
            counts[folder] += 1

    print(f"  ✅ {counts['images']} images  → replacements/images/")
    print(f"  ✅ {counts['gifs']} GIFs     → replacements/gifs/")
    print(f"  ✅ {counts['audio']} audio   → replacements/audio/")
    print(f"""
✅ Done! Files sorted into subfolders inside '{REPLACEMENTS_DIR}/'.

👉 Swap out whichever files you want, keeping the same filename.
   Images will be auto-resized — audio/GIFs swapped as-is.

Tip: run  python fnaf_mod.py preview  to see all images in your browser.

Then run:  python fnaf_mod.py repack
""")

def repack():
    if not os.path.exists(REPLACEMENTS_DIR):
        print("❌ No 'replacements/' folder found. Run 'python fnaf_mod.py extract' first.")
        return
    if not os.path.exists(RESOURCES_ZIP):
        print("❌ resources.zip not found. Run 'python fnaf_mod.py extract' first.")
        return

    try:
        from PIL import Image
    except ImportError:
        print("❌ Pillow not installed. Run:  pip install pillow")
        return

    print("🔍 Checking for replaced files...")
    replaced = []

    with zipfile.ZipFile(RESOURCES_ZIP, "r") as orig_zip:
        print("📦 Building modded zip...")
        with zipfile.ZipFile(MODDED_ZIP, "w", zipfile.ZIP_DEFLATED) as new_zip:
            for name in orig_zip.namelist():
                if is_media(name):
                    folder = subfolder_for(name)
                    filename = Path(name).name
                    replacement_path = os.path.join(REPLACEMENTS_DIR, folder, filename)

                    if os.path.exists(replacement_path):
                        orig_data = orig_zip.read(name)
                        with open(replacement_path, "rb") as f:
                            new_data = f.read()

                        if orig_data != new_data:
                            if is_image(name):
                                import io
                                orig_img = Image.open(io.BytesIO(orig_data))
                                orig_size = orig_img.size
                                new_img = Image.open(replacement_path)
                                if new_img.size != orig_size:
                                    print(f"  🔄 Resizing {name}: {new_img.size} → {orig_size}")
                                    new_img = new_img.resize(orig_size, Image.LANCZOS)
                                if orig_img.mode != new_img.mode:
                                    new_img = new_img.convert(orig_img.mode)
                                buf = io.BytesIO()
                                fmt = "PNG" if name.lower().endswith(".png") else "JPEG"
                                new_img.save(buf, format=fmt)
                                new_zip.writestr(name, buf.getvalue())
                            else:
                                new_zip.writestr(name, new_data)

                            replaced.append(name)
                            print(f"  ✅ Replaced [{Path(name).suffix.upper()}]: {name}")
                            continue

                new_zip.writestr(name, orig_zip.read(name))

    if not replaced:
        print("  ⚠️  No changed files found! Did you swap any files in replacements/?")
        os.remove(MODDED_ZIP)
        return

    print(f"\n✂️  Splitting into {PARTS} parts...")
    modded_size = os.path.getsize(MODDED_ZIP)
    part_size = (modded_size + PARTS - 1) // PARTS

    with open(MODDED_ZIP, "rb") as f:
        for i in range(1, PARTS + 1):
            chunk = f.read(part_size)
            if not chunk:
                break
            part_name = f"{PARTS_PREFIX}{i}"
            with open(part_name + ".modded", "wb") as pf:
                pf.write(chunk)
            print(f"  ✅ {part_name}.modded")

    print(f"\n✅ Done! {len(replaced)} file(s) replaced.\nRun:  python fnaf_mod.py activate")

def activate():
    print("🔄 Swapping part files...")
    for i in range(1, PARTS + 1):
        orig   = f"{PARTS_PREFIX}{i}"
        modded = orig + ".modded"
        if not os.path.exists(modded):
            print(f"  ❌ {modded} not found — run 'repack' first")
            return
        if os.path.exists(orig):
            os.remove(orig)
            print(f"  🗑️  Removed old {orig}")
        os.rename(modded, orig)
        print(f"  ✅ {orig} is now modded")
    print("\n✅ Activated! Run 'python fnaf_mod.py play' to launch.")

def restore():
    print("⚠️  No automatic restore (originals were not kept).")
    print("   Restore from GitHub:  git checkout -- .")

def preview():
    images_dir = os.path.join(REPLACEMENTS_DIR, "images")
    gifs_dir   = os.path.join(REPLACEMENTS_DIR, "gifs")

    if not os.path.exists(images_dir) and not os.path.exists(gifs_dir):
        print("❌ No replacements/images/ or replacements/gifs/ folder found.")
        print("   Run 'python fnaf_mod.py extract' first.")
        return

    print("🖼️  Generating preview...")

    def collect(folder, exts):
        if not os.path.exists(folder):
            return []
        return sorted(f for f in os.listdir(folder) if Path(f).suffix.lower() in exts)

    image_files = collect(images_dir, {".png", ".jpg"})
    gif_files   = collect(gifs_dir,   {".gif"})

    def img_card(filepath, filename):
        with open(filepath, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        ext  = Path(filename).suffix.lower().lstrip(".")
        mime = "gif" if ext == "gif" else ("jpeg" if ext == "jpg" else "png")
        return f"""
        <div class="card">
            <img src="data:image/{mime};base64,{data}" alt="{filename}" />
            <div class="label">{filename}</div>
        </div>"""

    cards_html = ""

    if image_files:
        cards_html += '<h2>🖼️ Images</h2><div class="grid">'
        for fname in image_files:
            cards_html += img_card(os.path.join(images_dir, fname), fname)
        cards_html += "</div>"

    if gif_files:
        cards_html += '<h2>🎞️ GIFs</h2><div class="grid">'
        for fname in gif_files:
            cards_html += img_card(os.path.join(gifs_dir, fname), fname)
        cards_html += "</div>"

    if not image_files and not gif_files:
        print("  ⚠️  No image or GIF files found to preview.")
        return

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>FNAF Mod Preview</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #111;
    color: #eee;
    font-family: 'Segoe UI', sans-serif;
    padding: 24px;
  }}
  h1 {{
    text-align: center;
    margin-bottom: 8px;
    font-size: 2rem;
    color: #f5a623;
  }}
  .subtitle {{
    text-align: center;
    color: #888;
    margin-bottom: 32px;
    font-size: 0.9rem;
  }}
  h2 {{
    color: #f5a623;
    margin: 32px 0 16px;
    font-size: 1.2rem;
    border-bottom: 1px solid #333;
    padding-bottom: 8px;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 16px;
  }}
  .card {{
    background: #1e1e1e;
    border: 1px solid #333;
    border-radius: 8px;
    overflow: hidden;
    text-align: center;
    transition: transform 0.15s, border-color 0.15s;
  }}
  .card:hover {{
    transform: scale(1.04);
    border-color: #f5a623;
  }}
  .card img {{
    width: 100%;
    height: 140px;
    object-fit: contain;
    background: #2a2a2a;
    padding: 4px;
    image-rendering: pixelated;
  }}
  .label {{
    padding: 8px 6px;
    font-size: 0.72rem;
    color: #ccc;
    word-break: break-all;
    line-height: 1.3;
  }}
</style>
</head>
<body>
<h1>🎮 FNAF Mod Preview</h1>
<p class="subtitle">Generated {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} &nbsp;·&nbsp; {len(image_files)} images, {len(gif_files)} GIFs</p>
{cards_html}
</body>
</html>"""

    out_path = "preview.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  ✅ {len(image_files)} images + {len(gif_files)} GIFs embedded")
    print(f"\n✅ Saved to '{out_path}' — opening in your browser...")

    try:
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(out_path)}")
    except Exception:
        pass

def backup():
    print("☁️  Backing up to GitHub...")

    if not os.path.exists(".git"):
        print("  🔧 No git repo found, initializing...")
        subprocess.run(["git", "init"], check=True)

    result = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True)
    if "origin" not in result.stdout:
        remote_url = input("  🔗 Enter your GitHub remote URL (e.g. https://github.com/user/repo.git): ").strip()
        if not remote_url:
            print("  ❌ No URL provided, aborting.")
            return
        subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
        print(f"  ✅ Remote set to {remote_url}")

    gitignore_entries = [
        RESOURCES_ZIP,
        MODDED_ZIP,
        "__pycache__/",
        "*.pyc",
        f"{REPLACEMENTS_DIR}/",
        "preview.html",
    ]
    if not os.path.exists(".gitignore"):
        with open(".gitignore", "w") as f:
            f.write("\n".join(gitignore_entries) + "\n")
        print("  📝 Created .gitignore")

    subprocess.run(["git", "add", "-A"], check=True)

    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if not status.stdout.strip():
        print("  ✅ Nothing new to commit — already up to date.")
        return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"mod backup {timestamp}"
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)

    print("  📤 Pushing to GitHub...")
    push = subprocess.run(["git", "push", "-u", "origin", "main"], capture_output=True, text=True)
    if push.returncode != 0:
        print(f"  ❌ Push failed:\n{push.stderr}")
        print("  💡 Make sure the repo exists on GitHub and you have push access.")
        return

    print(f"\n✅ Backed up to GitHub with commit: '{commit_msg}'")

def play():
    print("🎮 Starting local server at http://localhost:8000")
    print("   Open that URL in your browser to play.")
    print("   Press Ctrl+C to stop.\n")
    subprocess.run([sys.executable, "-m", "http.server", "8000"])

commands = {
    "extract":  extract,
    "repack":   repack,
    "activate": activate,
    "restore":  restore,
    "preview":  preview,
    "backup":   backup,
    "play":     play,
    "all":      lambda: (repack(), activate(), play()),
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print(__doc__)
        print("Commands: extract | repack | activate | restore | preview | backup | play")
    else:
        commands[sys.argv[1]]()