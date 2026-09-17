#!/usr/bin/env python3
"""
SORA Archive Multi-Repo Reindexer & Git Auto-Updater
====================================================
Menyatukan arsip video OpenAI Sora dari multiple repository GitHub:
  - yolajeni90/sora
  - yolajeni90/luqmanz
  - yolajeni90/sora-standup-1
  - yolajeni90/sora-standup-2
  - yolajeni90/sora-standup-3
  - (dan sora-standup-* berikutnya secara dinamis)

Serta langsung meng-commit dan push ke repository sora-player.

Penggunaan:
  python reindex.py
  python reindex.py --push
  python reindex.py --token "ghp_xxxxxxxxxxxx"
  python reindex.py --no-push
  python reindex.py --local-dir "../"
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_OWNER = "yolajeni90"
PLAYER_REPO = "sora-player"

BASE_REPOS = [
    {
        "id": "sora",
        "name": "sora",
        "owner": DEFAULT_OWNER,
        "repo": "sora",
        "branch": "main",
        "base_url": f"https://raw.githubusercontent.com/{DEFAULT_OWNER}/sora/main/",
        "local_path": "../sora/",
        "default_folder": None,  # folders parsed from repo path (acid, aiko, etc.)
    },
    {
        "id": "luqmanz",
        "name": "luqmanz",
        "owner": DEFAULT_OWNER,
        "repo": "luqmanz",
        "branch": "main",
        "base_url": f"https://raw.githubusercontent.com/{DEFAULT_OWNER}/luqmanz/main/",
        "local_path": "../luqmanz/",
        "default_folder": "luqmanz",  # unified category
    },
]


def discover_standup_repos(token=None):
    """Detect all sora-standup-* repositories dynamically (standup-1, 2, 3, etc.)."""
    standup_configs = []
    index = 1
    while True:
        repo_name = f"sora-standup-{index}"
        url = f"https://api.github.com/repos/{DEFAULT_OWNER}/{repo_name}"
        req = urllib.request.Request(url, headers={"User-Agent": "SoraReindexerPython/2.0"})
        if token:
            req.add_header("Authorization", f"token {token}")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    standup_configs.append({
                        "id": repo_name,
                        "name": repo_name,
                        "owner": DEFAULT_OWNER,
                        "repo": repo_name,
                        "branch": "main",
                        "base_url": f"https://raw.githubusercontent.com/{DEFAULT_OWNER}/{repo_name}/main/",
                        "local_path": f"../{repo_name}/",
                        "default_folder": "standup",  # All standup repos seamlessly merge into 'standup'
                    })
                    index += 1
                else:
                    break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # No more standup repositories found
                break
            elif e.code == 403:
                # Rate limited or forbidden; keep at least 1, 2, 3 as fallback
                print(f"[Info] API rate limit pada deteksi repositori, menggunakan default standup-1..3")
                break
            else:
                break
        except Exception:
            break

    # If dynamic discovery found none (e.g. offline or strict rate limit), fallback to known 1..3
    if not standup_configs:
        for idx in range(1, 4):
            repo_name = f"sora-standup-{idx}"
            standup_configs.append({
                "id": repo_name,
                "name": repo_name,
                "owner": DEFAULT_OWNER,
                "repo": repo_name,
                "branch": "main",
                "base_url": f"https://raw.githubusercontent.com/{DEFAULT_OWNER}/{repo_name}/main/",
                "local_path": f"../{repo_name}/",
                "default_folder": "standup",
            })

    return standup_configs


def natural_sort_key(s):
    """Sort strings with embedded numbers naturally (e.g. 001, 002, ..., 010)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def folder_priority(folder_name):
    """
    Folder priority rule:
      0: 'luqmanz' (always at the very beginning)
      1: regular folders ('acid', 'aiko', 'aix', ... 'yuni')
      2: 'standup' (always at the very end)
    """
    fn = (folder_name or "").lower()
    if fn == "luqmanz":
        return 0
    if fn.startswith("standup") or "standup" in fn:
        return 2
    return 1


def load_existing_cache(filepath, repo_configs):
    """Read existing videos from videos.js to use as fallback cache."""
    cache = {}
    if not os.path.exists(filepath):
        return cache

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        match = re.search(r'window\.SORA_MANIFEST\s*=\s*(\{[\s\S]*?\});?\s*$', content)
        if match:
            manifest = json.loads(match.group(1))
            videos = manifest.get("videos", [])
            for v in videos:
                r_idx = v.get("r", 0)
                repo_name = repo_configs[r_idx]["name"] if r_idx < len(repo_configs) else "sora"
                if repo_name not in cache:
                    cache[repo_name] = []
                cache[repo_name].append({
                    "r": r_idx,
                    "p": v.get("p", ""),
                    "f": v.get("f", ""),
                    "s": v.get("s", ""),
                    "n": v.get("n", ""),
                    "m": v.get("m", 0),
                })
    except Exception as e:
        print(f"[Info] Catatan cache: tidak dapat mem-parsing {filepath}: {e}")

    return cache


def fetch_github_tree(config, token=None, max_retries=3):
    """Fetch git tree recursively from GitHub API with retry logic."""
    url = f"https://api.github.com/repos/{config['owner']}/{config['repo']}/git/trees/{config['branch']}?recursive=1"
    headers = {
        "User-Agent": "SoraReindexerPython/2.0",
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[API] Mengambil daftar file: {config['owner']}/{config['repo']} ({config['branch']}) [Coba {attempt}/{max_retries}]...")
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                rate_remaining = resp.headers.get("x-ratelimit-remaining")
                if rate_remaining is not None:
                    print(f"      [RateLimit] Sisa kuota GitHub API: {rate_remaining}")

                raw_data = resp.read().decode("utf-8")
                data = json.loads(raw_data)
                tree = data.get("tree", [])

                mp4_files = []
                for item in tree:
                    if item.get("type") == "blob" and item.get("path", "").lower().endswith(".mp4"):
                        mp4_files.append({
                            "path": item["path"],
                            "size_bytes": item.get("size", 0)
                        })
                return mp4_files

        except urllib.error.HTTPError as e:
            last_error = e
            err_msg = f"HTTP {e.code} {e.reason}"
            try:
                body = json.loads(e.read().decode("utf-8"))
                if "message" in body:
                    err_msg += f" - {body['message']}"
            except Exception:
                pass
            print(f"      [Gagal] {err_msg}")
            if attempt < max_retries and e.code in (500, 502, 503, 504):
                time.sleep(3)
            else:
                break
        except Exception as e:
            last_error = e
            print(f"      [Gagal] {e}")
            if attempt < max_retries:
                time.sleep(3)

    raise last_error if last_error else RuntimeError("Gagal mengambil data GitHub.")


def scan_local_repo(repo_dir):
    """Scan local directory recursively for MP4 files."""
    results = []
    if not os.path.exists(repo_dir):
        return results

    for root, _, files in os.walk(repo_dir):
        for file in files:
            if file.lower().endswith(".mp4") and not file.startswith("."):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, repo_dir).replace("\\", "/")
                size_bytes = os.path.getsize(full_path)
                results.append({
                    "path": rel_path,
                    "size_bytes": size_bytes
                })
    return results


def process_files(files, config, repo_index):
    """Transform raw file records into unified manifest items."""
    processed = []
    for f in files:
        raw_path = f["path"]
        parts = raw_path.split("/")
        filename = parts[-1]
        size_mb = round(f["size_bytes"] / (1024 * 1024), 2)

        if config["default_folder"]:
            folder = config["default_folder"]
            subfolder = parts[0] if len(parts) > 1 else ""
        else:
            if len(parts) >= 3:
                folder = parts[0]
                subfolder = parts[1]
            elif len(parts) == 2:
                folder = parts[0]
                subfolder = ""
            else:
                folder = "root"
                subfolder = ""

        processed.append({
            "r": repo_index,
            "p": raw_path,
            "f": folder,
            "s": subfolder,
            "n": filename,
            "m": size_mb,
        })
    return processed


def perform_git_sync(repo_dir, token=None, commit_msg=None):
    """Commit changes and push to GitHub sora-player repository."""
    print("\n" + "-".repeat(65) if hasattr(str, 'repeat') else "-" * 65)
    print("🚀 PROSES GIT COMMIT & PUSH KE REPO SORA-PLAYER")
    print("-" * 65)

    # Check status
    res = subprocess.run(["git", "status", "--porcelain"], cwd=repo_dir, capture_output=True, text=True)
    if not res.stdout.strip():
        print("[Git] Tidak ada perubahan berkas untuk di-commit.")
    else:
        print("[Git] Menambahkan perubahan ke stage (git add)...")
        subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True)

        if not commit_msg:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_msg = f"Update video archive manifest & player: {timestamp}"

        print(f"[Git] Membuat commit: '{commit_msg}'...")
        commit_res = subprocess.run(["git", "commit", "-m", commit_msg], cwd=repo_dir, capture_output=True, text=True)
        if commit_res.returncode == 0:
            print(f"  ✓ Commit berhasil dibuat.")
        else:
            print(f"  Info: {commit_res.stdout.strip()}")

    # Determine push URL / command
    print("[Git] Melakukan push ke origin main...")
    push_cmd = ["git", "push"]

    if token:
        # Use authenticated push URL
        auth_url = f"https://{token}@github.com/{DEFAULT_OWNER}/{PLAYER_REPO}.git"
        push_cmd = ["git", "push", auth_url, "HEAD:main"]
    else:
        push_cmd = ["git", "push", "origin", "main"]

    push_res = subprocess.run(push_cmd, cwd=repo_dir, capture_output=True, text=True)
    if push_res.returncode == 0:
        print(f"  🎉 SUKSES: Perubahan berhasil di-push ke https://github.com/{DEFAULT_OWNER}/{PLAYER_REPO}!")
        return True
    else:
        print(f"  ⚠️  Git push mengalami kendala:")
        err_output = push_res.stderr.strip() or push_res.stdout.strip()
        print(f"     {err_output}")
        if "403" in err_output or "Permission" in err_output:
            print("\n  [PETUNJUK OTENTIKASI]:")
            print("  Akun Git yang tersimpan di sistem tidak memiliki izin write ke repositori yolajeni90/sora-player.")
            print("  Gunakan Personal Access Token (PAT) GitHub Anda dengan perintah:")
            print(f"    python reindex.py --push --token \"ghp_YOUR_TOKEN_HERE\"")
            print("  Atau jalankan 'git push' secara manual di sesi terminal Anda yang telah terotentikasi.")
        return False


def get_git_credential_token():
    """Retrieve GitHub token automatically from git credential helper if available."""
    try:
        proc = subprocess.Popen(
            ["git", "credential", "fill"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        out, _ = proc.communicate(input="protocol=https\nhost=github.com\n\n", timeout=5)
        for line in out.splitlines():
            if line.startswith("password="):
                tok = line.split("=", 1)[1].strip()
                if tok:
                    return tok
    except Exception:
        pass
    return ""


def main():
    parser = argparse.ArgumentParser(description="Sora Archive Multi-Repo Python Reindexer & Git Syncer")
    parser.add_argument("--token", default="",
                        help="GitHub Personal Access Token (PAT)")
    parser.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos.js"),
                        help="Path output file videos.js")
    parser.add_argument("--local-dir", default="",
                        help="Direktori yang berisi clone lokal dari repositori video")
    parser.add_argument("--push", dest="push", action="store_true", default=True,
                        help="Otomatis commit dan push ke GitHub (default: True)")
    parser.add_argument("--no-push", dest="push", action="store_false",
                        help="Jangan lakukan git push setelah reindex")
    parser.add_argument("--commit-msg", default="",
                        help="Pesan commit git kustom")

    args = parser.parse_args()
    cwd = os.path.dirname(os.path.abspath(__file__))

    # Auto-detect token from argument, environment, or git credential helper
    token = args.token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or get_git_credential_token()

    print("=" * 65)
    print("🎬 SORA ARCHIVE MULTI-REPO REINDEXER (PYTHON)")
    print("=" * 65)
    print(f"Target Output : {args.out}")
    print(f"Mode          : {'Lokal Disk (' + args.local_dir + ')' if args.local_dir else 'Online GitHub API'}")
    print(f"Otentikasi    : {'Token Terdeteksi' if token else 'Anonim'}")
    print(f"Auto Git Push : {'Aktif' if args.push else 'Nonaktif'}")
    print("-" * 65)

    # Discover repositories
    print("[Discovery] Mendeteksi seluruh repositori sora-standup-*...")
    standup_repos = discover_standup_repos(token)
    repo_configs = BASE_REPOS + standup_repos
    print(f"            Ditemukan {len(repo_configs)} target repositori: {', '.join(r['name'] for r in repo_configs)}")

    # Load cache
    existing_cache = load_existing_cache(args.out, repo_configs)
    if existing_cache:
        print(f"[Cache] Ditemukan cache tersedia: {', '.join(f'{k} ({len(v)})' for k, v in existing_cache.items())}")

    all_videos = []
    repo_stats = {}
    folder_stats = {}

    for idx, config in enumerate(repo_configs):
        file_list = None
        try:
            if args.local_dir:
                local_path = os.path.join(args.local_dir, config["repo"])
                print(f"[Lokal] Membaca folder: {local_path}...")
                if os.path.exists(local_path):
                    file_list = scan_local_repo(local_path)
                else:
                    print(f"  [Peringatan] Folder lokal '{local_path}' tidak ditemukan.")
            else:
                file_list = fetch_github_tree(config, token)

            if file_list is not None:
                videos = process_files(file_list, config, idx)
                repo_stats[config["name"]] = len(videos)
                print(f"  ✓ Berhasil memuat {len(videos):,} video dari '{config['name']}'")
                all_videos.extend(videos)
                continue
        except Exception as e:
            print(f"  ✗ Gagal mengambil langsung '{config['name']}': {e}")

        # Fallback to cache if fetch failed
        cached = existing_cache.get(config["name"], [])
        if cached:
            for item in cached:
                item["r"] = idx
            print(f"  ⚡ [Fallback Cache] Menggunakan {len(cached):,} video dari cache untuk '{config['name']}'")
            repo_stats[config["name"]] = f"{len(cached):,} (dari cache)"
            all_videos.extend(cached)
        else:
            repo_stats[config["name"]] = "0 (Gagal & tidak ada cache)"

    if not all_videos:
        print("\n[Error Fatal] Tidak ada video yang berhasil diindeks.")
        sys.exit(1)

    print("\n[Sorting] Mengurutkan seluruh koleksi (luqmanz di awal, standup di akhir)...")
    all_videos.sort(key=lambda v: (
        folder_priority(v["f"]),
        v["f"].lower(),
        natural_sort_key(v["s"]),
        natural_sort_key(v["n"])
    ))

    for v in all_videos:
        folder_stats[v["f"]] = folder_stats.get(v["f"], 0) + 1

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    manifest = {
        "baseUrl": repo_configs[0]["base_url"],
        "mode": "Multi-Repo Unified Archive",
        "generatedAt": now_str,
        "totalCount": len(all_videos),
        "repos": [
            {
                "id": c["id"],
                "name": c["name"],
                "baseUrl": c["base_url"],
                "localPath": c["local_path"],
            }
            for c in repo_configs
        ],
        "videos": all_videos,
    }

    manifest_json = json.dumps(manifest, separators=(',', ':'))
    file_content = (
        f"// SORA Video Gallery Manifest (Generated on {now_str})\n"
        f"// Mode: Multi-Repo Unified Archive | Total Videos: {len(all_videos)}\n"
        f"// Repositories included: {', '.join(r['name'] for r in repo_configs)}\n"
        f"window.SORA_MANIFEST = {manifest_json};\n"
    )

    print(f"[Writing] Menulis ke file '{args.out}'...")
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(file_content)

    file_size = os.path.getsize(args.out)
    file_size_mb = round(file_size / (1024 * 1024), 2)

    print("\n" + "=" * 65)
    print("🎉 REINDEX SELESAI DENGAN SUKSES!")
    print("=" * 65)
    print(f"Total Video Terindeks : {len(all_videos):,} video")
    print(f"Total Folder Kategori : {len(folder_stats):,} folder")
    print(f"Ukuran File videos.js : {file_size_mb} MB ({file_size:,} bytes)")
    print("\nRincian per Repository:")
    for r_name, count in repo_stats.items():
        val = f"{count:,} video" if isinstance(count, int) else count
        print(f"  - {r_name.ljust(20)}: {val}")

    print("\nRincian Folder Utama (Kategori):")
    sorted_folders = sorted(folder_stats.items(), key=lambda x: (folder_priority(x[0]), x[0].lower()))
    for f_name, count in sorted_folders:
        print(f"  - {f_name.ljust(16)}: {count:,} video")
    print("=" * 65)

    # Git Sync
    if args.push:
        commit_msg = args.commit_msg or f"Update video archive manifest: {len(all_videos):,} videos ({now_str})"
        perform_git_sync(cwd, token=token, commit_msg=commit_msg)


if __name__ == "__main__":
    main()
