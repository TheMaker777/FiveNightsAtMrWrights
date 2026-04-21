"""
FNAF Teacher Mod Tool
=====================
HOW TO USE:
1. Put this script in the same folder as your game files (index.html, main.js, etc.)
2. Run:  python fnaf_mod.py extract
   → This pulls all images, audio, and gifs out into a folder called "replacements/"
3. Open the "replacements/" folder and swap out whichever files you want
   (replacement images will be auto-resized to match the original size)
4. Run:  python fnaf_mod.py repack
   → This rebuilds the game with your new files, ready to play!

To play the modded game: run  python fnaf_mod.py play
Then open http://localhost:8000 in your browser.

To back up to GitHub: run  python fnaf_mod.py backup
"""

# use python fnaf_mod.py extract, repack, activate, play, backup

import os, sys, shutil, zipfile, struct, subprocess
from pathlib import Path

PARTS = 8
PARTS_PREFIX = "resources.zip.part"
RESOURCES_ZIP = "resources.zip"
REPLACEMENTS_DIR = "replacements"
MODDED_ZIP = "resources_modded.zip"

MEDIA_EXTENSIONS = (".png", ".jpg", ".gif", ".ogg", ".mp3")
IMAGE_EXTENSIONS = (".png", ".jpg")
RESIZABLE_EXTENSIONS = (".png", ".jpg")

def is_media(name):
    return name.lower().endswith(MEDIA_EXTENSIONS)

def is_image(name):
    return name.lower().endswith(IMAGE_EXTENSIONS)

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

    print(f"\n📂 Extracting media files to '{REPLACEMENTS_DIR}/'...")
    os.makedirs(REPLACEMENTS_DIR, exist_ok=True)

    with zipfile.ZipFile(RESOURCES_ZIP, "r") as z:
        media_files = [n for n in z.namelist() if is_media(n)]
        for name in media_files:
            z.extract(name, REPLACEMENTS_DIR)
        
        counts = {
            "images": sum(1 for n in media_files if is_image(n)),
            "gifs":   sum(1 for n in media_files if n.lower().endswith(".gif")),
            "audio":  sum(1 for n in media_files if n.lower().endswith((".ogg", ".mp3"))),
        }
        print(f"  ✅ Extracted {counts['images']} images, {counts['gifs']} GIFs, {counts['audio']} audio files")

    print(f"""
✅ Done! Your files are in the '{REPLACEMENTS_DIR}/' folder.

👉 Swap out whichever files you want with your replacements.
   Name your replacement file the same as the original (e.g. M0003.png)
   Images will be auto-resized — audio/GIFs are swapped as-is.

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
        print(f"📦 Building modded zip...")
        with zipfile.ZipFile(MODDED_ZIP, "w", zipfile.ZIP_DEFLATED) as new_zip:
            for name in orig_zip.namelist():
                replacement_path = os.path.join(REPLACEMENTS_DIR, name)

                if os.path.exists(replacement_path) and is_media(name):
                    orig_data = orig_zip.read(name)
                    with open(replacement_path, "rb") as f:
                        new_data = f.read()

                    if orig_data != new_data:
                        # For images, resize to match original dimensions
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
                            # GIF / audio — swap as-is
                            new_zip.writestr(name, new_data)

                        replaced.append(name)
                        ext = Path(name).suffix.upper()
                        print(f"  ✅ Replaced [{ext}]: {name}")
                        continue

                # Keep original
                new_zip.writestr(name, orig_zip.read(name))

    if not replaced:
        print("  ⚠️  No changed files found! Did you actually swap any files in replacements/?")
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

    print(f"""
✅ Done! {len(replaced)} file(s) replaced.

Your modded part files are named resources.zip.part1.modded ... part8.modded

To activate them run:  python fnaf_mod.py activate
""")

def activate():
    print("🔄 Swapping part files...")
    for i in range(1, PARTS + 1):
        orig = f"{PARTS_PREFIX}{i}"
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
    print("⚠️  No automatic restore available (originals were not kept).")
    print("   To restore, re-run 'python fnaf_mod.py extract' from your original part files,")
    print("   or grab the originals from your GitHub backup:")
    print("   git checkout -- .")

def backup():
    print("☁️  Backing up to GitHub...")

    # Init repo if not already one
    if not os.path.exists(".git"):
        print("  🔧 No git repo found, initializing...")
        subprocess.run(["git", "init"], check=True)

    # Check for remote
    result = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True)
    if "origin" not in result.stdout:
        remote_url = input("  🔗 Enter your GitHub remote URL (e.g. https://github.com/user/repo.git): ").strip()
        if not remote_url:
            print("  ❌ No URL provided, aborting.")
            return
        subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
        print(f"  ✅ Remote set to {remote_url}")

    # Create .gitignore if it doesn't exist
    gitignore_path = ".gitignore"
    gitignore_entries = [
        RESOURCES_ZIP,
        MODDED_ZIP,
        "__pycache__/",
        "*.pyc",
        f"{REPLACEMENTS_DIR}/",
    ]
    if not os.path.exists(gitignore_path):
        with open(gitignore_path, "w") as f:
            f.write("\n".join(gitignore_entries) + "\n")
        print(f"  📝 Created .gitignore")
    
    subprocess.run(["git", "add", "-A"], check=True)

    # Check if there's anything to commit
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if not status.stdout.strip():
        print("  ✅ Nothing new to commit — already up to date.")
        return

    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"mod backup {timestamp}"
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)

    # Push (try main then master)
    print("  📤 Pushing to GitHub...")
    push = subprocess.run(["git", "push", "-u", "origin", "main"], capture_output=True, text=True)
    if push.returncode != 0:
        push = subprocess.run(["git", "push", "-u", "origin", "master"], capture_output=True, text=True)
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
    "backup":   backup,
    "play":     play,
    "all":      lambda: (repack(), activate(), play())
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print(__doc__)
        print("Commands: extract | repack | activate | restore | backup | play")
    else:
        commands[sys.argv[1]]()