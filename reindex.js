/**
 * SORA Archive Unified Reindexer
 * Re-indexes videos from 5 repositories into a single seamless manifest:
 *  - yolajeni90/sora
 *  - yolajeni90/luqmanz
 *  - yolajeni90/sora-standup-1
 *  - yolajeni90/sora-standup-2
 *  - yolajeni90/sora-standup-3
 *
 * Usage:
 *   node reindex.js
 *   node reindex.js --token YOUR_GITHUB_TOKEN
 *   node reindex.js --local-dir ../ (to index local cloned repos)
 */

const fs = require('fs');
const path = require('path');

const REPO_CONFIGS = [
  {
    id: 'sora',
    name: 'sora',
    owner: 'yolajeni90',
    repo: 'sora',
    branch: 'main',
    baseUrl: 'https://raw.githubusercontent.com/yolajeni90/sora/main/',
    localPath: '../sora/',
    defaultFolder: null // folders derived from path in repo (acid, aiko, etc.)
  },
  {
    id: 'luqmanz',
    name: 'luqmanz',
    owner: 'yolajeni90',
    repo: 'luqmanz',
    branch: 'main',
    baseUrl: 'https://raw.githubusercontent.com/yolajeni90/luqmanz/main/',
    localPath: '../luqmanz/',
    defaultFolder: 'luqmanz' // unified folder name
  },
  {
    id: 'sora-standup-1',
    name: 'sora-standup-1',
    owner: 'yolajeni90',
    repo: 'sora-standup-1',
    branch: 'main',
    baseUrl: 'https://raw.githubusercontent.com/yolajeni90/sora-standup-1/main/',
    localPath: '../sora-standup-1/',
    defaultFolder: 'standup' // merged seamlessly under 'standup'
  },
  {
    id: 'sora-standup-2',
    name: 'sora-standup-2',
    owner: 'yolajeni90',
    repo: 'sora-standup-2',
    branch: 'main',
    baseUrl: 'https://raw.githubusercontent.com/yolajeni90/sora-standup-2/main/',
    localPath: '../sora-standup-2/',
    defaultFolder: 'standup' // merged seamlessly under 'standup'
  },
  {
    id: 'sora-standup-3',
    name: 'sora-standup-3',
    owner: 'yolajeni90',
    repo: 'sora-standup-3',
    branch: 'main',
    baseUrl: 'https://raw.githubusercontent.com/yolajeni90/sora-standup-3/main/',
    localPath: '../sora-standup-3/',
    defaultFolder: 'standup' // merged seamlessly under 'standup'
  }
];

// Parse command line arguments
function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    token: process.env.GITHUB_TOKEN || '',
    out: path.join(__dirname, 'videos.js'),
    localDir: ''
  };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--token' && args[i + 1]) {
      options.token = args[++i];
    } else if (args[i] === '--out' && args[i + 1]) {
      options.out = path.resolve(args[++i]);
    } else if (args[i] === '--local-dir' && args[i + 1]) {
      options.localDir = path.resolve(args[++i]);
    } else if (args[i] === '--help' || args[i] === '-h') {
      console.log(`
Sora Archive Reindexer
======================
Options:
  --token <GITHUB_TOKEN>   GitHub personal access token (recommended if rate limited)
  --out <filepath>         Output path for videos.js (default: ./videos.js)
  --local-dir <path>       Directory containing local clones of the repos
  --help, -h               Show this help message
`);
      process.exit(0);
    }
  }

  return options;
}

const vm = require('vm');

// Read existing videos from target output file as cache
function loadExistingCache(filePath) {
  const cache = {};
  if (!fs.existsSync(filePath)) return cache;

  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const sandbox = { window: {} };
    vm.runInNewContext(content, sandbox);
    const manifest = sandbox.window && sandbox.window.SORA_MANIFEST;
    if (manifest && Array.isArray(manifest.videos)) {
      for (const v of manifest.videos) {
        const rIndex = (v.r !== undefined) ? v.r : 0;
        const repoName = REPO_CONFIGS[rIndex] ? REPO_CONFIGS[rIndex].name : 'sora';
        if (!cache[repoName]) cache[repoName] = [];
        cache[repoName].push({
          r: rIndex,
          p: v.p,
          f: v.f,
          s: v.s || '',
          n: v.n,
          m: v.m
        });
      }
    }
  } catch (err) {
    console.warn(`[Info] Tidak dapat membaca cache dari ${filePath}: ${err.message}`);
  }

  return cache;
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Fetch git tree via GitHub API with retry
async function fetchGitHubRepoTree(config, token, maxRetries = 2) {
  const url = `https://api.github.com/repos/${config.owner}/${config.repo}/git/trees/${config.branch}?recursive=1`;
  const headers = {
    'User-Agent': 'SoraArchiveReindexer/2.0',
    'Accept': 'application/vnd.github.v3+json'
  };

  if (token) {
    headers['Authorization'] = `token ${token}`;
  }

  let lastError = null;

  for (let attempt = 1; attempt <= maxRetries + 1; attempt++) {
    try {
      console.log(`[API] Mengambil daftar file dari GitHub: ${config.owner}/${config.repo} (${config.branch}) [Coba ${attempt}/${maxRetries + 1}]...`);
      const res = await fetch(url, { headers });

      const remaining = res.headers.get('x-ratelimit-remaining');
      if (remaining !== null) {
        console.log(`      [RateLimit] Sisa kuota GitHub API: ${remaining}`);
      }

      if (!res.ok) {
        const errText = await res.text();
        let errMsg = `HTTP ${res.status} ${res.statusText}`;
        try {
          const errJson = JSON.parse(errText);
          if (errJson.message) errMsg += ` - ${errJson.message}`;
        } catch (_) {}
        throw new Error(errMsg);
      }

      const data = await res.json();
      if (!data.tree || !Array.isArray(data.tree)) {
        throw new Error(`Format respons tidak valid untuk repo ${config.repo}`);
      }

      return (data.tree || [])
        .filter(item => item.type === 'blob' && item.path.toLowerCase().endsWith('.mp4'))
        .map(item => ({
          path: item.path,
          sizeBytes: item.size || 0
        }));
    } catch (err) {
      lastError = err;
      console.warn(`      [Percobaan Gagal] ${err.message}`);
      if (attempt <= maxRetries) {
        console.log(`      [Menunggu] Coba lagi dalam 3 detik...`);
        await delay(3000);
      }
    }
  }

  throw lastError;
}

// Recursively scan local folder for MP4 files
function scanLocalRepo(repoDir) {
  const results = [];

  function walk(currentDir, relativePrefix) {
    if (!fs.existsSync(currentDir)) return;
    const entries = fs.readdirSync(currentDir, { withFileTypes: true });
    for (const ent of entries) {
      if (ent.name.startsWith('.')) continue; // ignore .git, etc.
      const fullPath = path.join(currentDir, ent.name);
      const relPath = relativePrefix ? `${relativePrefix}/${ent.name}` : ent.name;

      if (ent.isDirectory()) {
        walk(fullPath, relPath);
      } else if (ent.isFile() && ent.name.toLowerCase().endsWith('.mp4')) {
        const stats = fs.statSync(fullPath);
        results.push({
          path: relPath.replace(/\\/g, '/'),
          sizeBytes: stats.size
        });
      }
    }
  }

  walk(repoDir, '');
  return results;
}

// Transform file records into standard manifest format
function processFileRecords(files, config, repoIndex) {
  const processed = [];

  for (const f of files) {
    const parts = f.path.split('/');
    const sizeMb = parseFloat((f.sizeBytes / (1024 * 1024)).toFixed(2));
    const filename = parts[parts.length - 1];

    let folder = '';
    let subfolder = '';

    if (config.defaultFolder) {
      folder = config.defaultFolder;
      if (parts.length > 1) {
        subfolder = parts[0];
      }
    } else {
      // sora repo format: folder/subfolder/file or folder/file
      if (parts.length >= 3) {
        folder = parts[0];
        subfolder = parts[1];
      } else if (parts.length === 2) {
        folder = parts[0];
        subfolder = '';
      } else {
        folder = 'root';
        subfolder = '';
      }
    }

    processed.push({
      r: repoIndex,
      p: f.path,
      f: folder,
      s: subfolder,
      n: filename,
      m: sizeMb
    });
  }

  return processed;
}

function getFolderPriority(folderName) {
  const fn = (folderName || '').toLowerCase();
  if (fn === 'luqmanz') return 0;
  if (fn.startsWith('standup') || fn.includes('standup')) return 2;
  return 1;
}

// Natural sorting helper for folder, subfolder, and filenames (luqmanz first, standup last)
function compareVideos(a, b) {
  const prioA = getFolderPriority(a.f);
  const prioB = getFolderPriority(b.f);
  if (prioA !== prioB) return prioA - prioB;
  if (a.f !== b.f) return a.f.localeCompare(b.f, undefined, { numeric: true, sensitivity: 'base' });
  if (a.s !== b.s) return a.s.localeCompare(b.s, undefined, { numeric: true, sensitivity: 'base' });
  return a.n.localeCompare(b.n, undefined, { numeric: true, sensitivity: 'base' });
}

// Main indexing function
async function main() {
  const options = parseArgs();
  console.log('='.repeat(65));
  console.log('🎬 SORA ARCHIVE MULTI-REPO REINDEXER');
  console.log('='.repeat(65));
  console.log(`Target Output: ${options.out}`);
  if (options.localDir) {
    console.log(`Mode: Lokal Disk (${options.localDir})`);
  } else {
    console.log(`Mode: Online GitHub API`);
  }
  console.log('-'.repeat(65));

  // Load existing cache in case of API limits or temporary network errors
  const existingCache = loadExistingCache(options.out);
  const cacheRepoNames = Object.keys(existingCache);
  if (cacheRepoNames.length > 0) {
    console.log(`[Cache] Ditemukan data cache yang tersedia: ${cacheRepoNames.map(k => `${k} (${existingCache[k].length})`).join(', ')}`);
  }

  const allVideos = [];
  const repoStats = {};
  const folderStats = {};

  for (let idx = 0; idx < REPO_CONFIGS.length; idx++) {
    const config = REPO_CONFIGS[idx];
    let fileList = null;

    try {
      if (options.localDir) {
        const localRepoPath = path.join(options.localDir, config.repo);
        console.log(`[Lokal] Membaca folder: ${localRepoPath}...`);
        if (fs.existsSync(localRepoPath)) {
          fileList = scanLocalRepo(localRepoPath);
        } else {
          console.warn(`[Peringatan] Folder lokal '${localRepoPath}' tidak ditemukan.`);
        }
      } else {
        fileList = await fetchGitHubRepoTree(config, options.token);
      }

      if (fileList) {
        const repoVideos = processFileRecords(fileList, config, idx);
        repoStats[config.name] = repoVideos.length;
        console.log(`  ✓ Berhasil memuat ${repoVideos.length.toLocaleString()} video dari '${config.name}'`);
        allVideos.push(...repoVideos);
        continue;
      }
    } catch (err) {
      console.error(`  ✗ Gagal mengambil langsung '${config.name}': ${err.message}`);
    }

    // Graceful fallback to existing cache if fetch failed
    if (existingCache[config.name] && existingCache[config.name].length > 0) {
      const cached = existingCache[config.name].map(v => ({ ...v, r: idx }));
      console.log(`  ⚡ [Fallback] Menggunakan ${cached.length.toLocaleString()} video dari cache untuk '${config.name}'`);
      repoStats[config.name] = `${cached.length.toLocaleString()} (dari cache)`;
      allVideos.push(...cached);
    } else {
      repoStats[config.name] = `0 (Gagal & tidak ada cache)`;
    }
  }

  if (allVideos.length === 0) {
    console.error('\n[Error Fatal] Tidak ada video yang berhasil diindeks.');
    process.exit(1);
  }

  console.log('\n[Sorting] Mengurutkan seluruh koleksi secara alfabetis dan hierarkis...');
  allVideos.sort(compareVideos);

  // Compute folder statistics
  for (const v of allVideos) {
    folderStats[v.f] = (folderStats[v.f] || 0) + 1;
  }

  const now = new Date();
  const dateStr = now.toISOString().replace('T', ' ').substring(0, 19);

  const manifest = {
    baseUrl: REPO_CONFIGS[0].baseUrl, // backwards compatibility
    mode: 'Multi-Repo Unified Archive',
    generatedAt: dateStr,
    totalCount: allVideos.length,
    repos: REPO_CONFIGS.map(c => ({
      id: c.id,
      name: c.name,
      baseUrl: c.baseUrl,
      localPath: c.localPath
    })),
    videos: allVideos
  };

  const fileContent = `// SORA Video Gallery Manifest (Generated on ${dateStr})
// Mode: Multi-Repo Unified Archive | Total Videos: ${allVideos.length}
// Repositories included: ${REPO_CONFIGS.map(r => r.name).join(', ')}
window.SORA_MANIFEST = ${JSON.stringify(manifest)};
`;

  console.log(`[Writing] Menulis ke file '${options.out}'...`);
  fs.writeFileSync(options.out, fileContent, 'utf8');

  const fileSizeBytes = fs.statSync(options.out).size;
  const fileSizeMb = (fileSizeBytes / (1024 * 1024)).toFixed(2);

  console.log('\n' + '='.repeat(65));
  console.log('🎉 REINDEX SELESAI DENGAN SUKSES!');
  console.log('='.repeat(65));
  console.log(`Total Video Terindeks : ${allVideos.length.toLocaleString()} video`);
  console.log(`Total Folder Kategori : ${Object.keys(folderStats).length} folder`);
  console.log(`Ukuran File videos.js : ${fileSizeMb} MB (${fileSizeBytes.toLocaleString()} bytes)`);
  console.log('\nRincian per Repository:');
  for (const [rName, count] of Object.entries(repoStats)) {
    console.log(`  - ${rName.padEnd(20)}: ${typeof count === 'number' ? count.toLocaleString() + ' video' : count}`);
  }
  console.log('\nRincian Folder Utama (Kategori):');
  for (const [fName, count] of Object.entries(folderStats).sort((a,b) => b[1] - a[1])) {
    console.log(`  - ${fName.padEnd(16)}: ${count.toLocaleString()} video`);
  }
  console.log('='.repeat(65));
}

main().catch(err => {
  console.error('\nFatal Error:', err);
  process.exit(1);
});
