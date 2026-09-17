# 🎬 SORA Archive Player (Unified Multi-Repo Vault)

Pemutar dan penjelajah galeri video arsip OpenAI Sora yang menyatukan **21.511 video** dari **5 repository terpisah** secara seamless tanpa terlihat terpisah oleh pengguna.

---

## 🌐 5 Repository yang Disatukan

Koleksi video ini dipecah ke dalam 5 repository GitHub demi efisiensi batas kuota ukuran repository, namun dipersatukan menjadi 1 arsip terpadu di player ini:

| Repository | Jumlah Video | Kategori di Player | Keterangan |
| :--- | :--- | :--- | :--- |
| **[`yolajeni90/sora`](https://github.com/yolajeni90/sora)** | 13.517 | `kokolaty`, `yuni`, `radinx`, dll. (27 folder) | Koleksi utama beragam tema |
| **[`yolajeni90/luqmanz`](https://github.com/yolajeni90/luqmanz)** | 2.795 | `luqmanz` (subfolder `001` .. `240`) | Arsip video Luqmanz |
| **[`yolajeni90/sora-standup-1`](https://github.com/yolajeni90/sora-standup-1)** | 2.062 | `standup` (subfolder `011` .. `031`) | Bagian 1 seri Standup |
| **[`yolajeni90/sora-standup-2`](https://github.com/yolajeni90/sora-standup-2)** | 2.034 | `standup` (subfolder `080` .. `099`) | Bagian 2 seri Standup |
| **[`yolajeni90/sora-standup-3`](https://github.com/yolajeni90/sora-standup-3)** | 1.103 | `standup` (subfolder `148` .. `159`) | Bagian 3 seri Standup |
| **TOTAL KESELURUHAN** | **21.511** | **29 Kategori Folder** | **1 Arsip Utuh** |

> **Catatan Seamless:** Seri `sora-standup-1`, `sora-standup-2`, dan `sora-standup-3` secara otomatis digabungkan di bawah folder kategori **`standup`**. Pengguna dapat menyaring subfolder (`011` s/d `159`) layaknya satu repositori besar.

---

## 🚀 Cara Menjalankan Player

Cukup buka [`index.html`](file:///E:/sora-player/index.html) langsung di peramban web (Chrome, Edge, Firefox, dsb.):
* Setiap video otomatis diselesaikan ke URL path absolut ke file MP4 di repository masing-masing melalui **GitHub Raw CDN** yang mendukung CORS & *byte-range streaming*.
* Semua **21.511 video** dapat langsung diputar secara instan dan lancar saat membuka file HTML lokal tanpa perlu mendownload file MP4 ke komputer.

---

## 🔄 Cara Menjalankan Skrip Reindex

Skrip reindex Python ([`reindex.py`](file:///E:/sora-player/reindex.py)) dapat dijalankan langsung untuk me-reindex seluruh repository dan otomatis commit serta push ke repository `sora-player`:

### 🐍 Menggunakan Python (Direkomendasikan)
```bash
# Reindex otomatis dari GitHub API + Auto Git Commit & Push
python reindex.py

# Menggunakan Personal Access Token (PAT) GitHub untuk kuota 5.000 req/jam & auth push:
python reindex.py --push --token "ghp_YOUR_TOKEN_HERE"

# Reindex langsung dari folder repositori lokal di komputer (tanpa batas kuota API):
python reindex.py --local-dir ".."

# Reindex saja tanpa melakukan git push:
python reindex.py --no-push
```

### ⚡ Menggunakan Node.js / PowerShell (Alternatif)
```bash
# Reindex otomatis dari GitHub API
node reindex.js

# Menggunakan token jika kuota rate-limit habis
node reindex.js --token "ghp_xxxxxxxxxxxx"

# Reindex dari folder lokal (jika file ada di harddisk)
node reindex.js --local-dir "../"
```

### Menggunakan PowerShell (Windows)
```powershell
# Jalankan reindex default
.\reindex.ps1

# Atau menggunakan nama alias lama
.\update_gallery.ps1

# Dengan GitHub Token
.\reindex.ps1 -Token "ghp_xxxxxxxxxxxx"

# Dari folder lokal
.\reindex.ps1 -LocalDir ".."
```

---

## ⌨️ Pintasan Keyboard (Shortcuts)

* <kbd>Space</kbd>: Putar / Jeda video (Play / Pause).
* <kbd>◀</kbd> / <kbd>▶</kbd>: Pindah ke video sebelumnya / berikutnya.
* <kbd>R</kbd>: Putar video acak (*Random Video*).
* <kbd>J</kbd>: Fokus ke input lompat nomor video (*Jump to Video Number*).
* <kbd>Esc</kbd>: Tutup pop-up pemutar video.
