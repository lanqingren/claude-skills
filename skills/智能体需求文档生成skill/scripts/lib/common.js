'use strict';

const fs = require('fs');
const path = require('path');

function camelCase(key) {
  return String(key || '').replace(/-([a-z])/g, (_, c) => c.toUpperCase());
}

function parseCliArgs(rawArgs) {
  const args = {};

  for (let i = 0; i < rawArgs.length; i += 1) {
    const current = rawArgs[i];
    if (!current.startsWith('--')) continue;

    const key = camelCase(current.slice(2));
    const next = rawArgs[i + 1];
    if (next && !next.startsWith('--')) {
      args[key] = next;
      i += 1;
    } else {
      args[key] = true;
    }
  }

  return args;
}

function normalizePath(targetPath, baseDir = process.cwd()) {
  if (!targetPath) return null;
  return path.isAbsolute(targetPath)
    ? targetPath
    : path.resolve(baseDir, targetPath);
}

function ensureDir(dirPath) {
  if (!dirPath) {
    throw new Error('目录不能为空');
  }
  fs.mkdirSync(dirPath, { recursive: true });
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function sanitizeFileStem(name) {
  return String(name || '')
    .trim()
    .replace(/[\\/:*?"<>|]/g, '-')
    .replace(/\s+/g, ' ');
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function replaceTokens(template, values) {
  return template.replace(/\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g, (match, key) => {
    const value = values[key];
    return value === undefined || value === null ? match : String(value);
  });
}

function parseVersionFromText(content) {
  const patterns = [
    /\|\s*文档版本\s*\|\s*(v[\d.]+)\s*\|/i,
    /^docVersion:\s*(v[\d.]+)$/im,
    /文档版本[:：]\s*(v[\d.]+)/i,
    /版本[:：]\s*(v[\d.]+)/i,
  ];

  for (const pattern of patterns) {
    const matched = content.match(pattern);
    if (matched) return matched[1];
  }

  return null;
}

function readVersionFromMd(filePath) {
  if (!fs.existsSync(filePath)) return null;
  const content = fs.readFileSync(filePath, 'utf8');
  return parseVersionFromText(content);
}

function escapeRegExp(input) {
  return input.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function archiveOldSnapshots(outDir, baseName, backupDirName = 'backup') {
  ensureDir(outDir);
  const backupDir = path.join(outDir, backupDirName);
  ensureDir(backupDir);

  const archived = [];
  const re = new RegExp(`^${escapeRegExp(baseName)}_v[\\d.]+\\.md$`);
  fs.readdirSync(outDir).forEach((file) => {
    if (re.test(file)) {
      fs.renameSync(path.join(outDir, file), path.join(backupDir, file));
      archived.push(file);
    }
  });

  return archived;
}

function loadProfile(profilePath) {
  const absolutePath = normalizePath(profilePath);
  if (!absolutePath || !fs.existsSync(absolutePath)) {
    throw new Error(`找不到 profile 文件：${profilePath}`);
  }
  return {
    path: absolutePath,
    dir: path.dirname(absolutePath),
    data: readJson(absolutePath),
  };
}

function loadManifestEntries(manifestPath) {
  const absolutePath = normalizePath(manifestPath);
  if (!absolutePath || !fs.existsSync(absolutePath)) {
    throw new Error(`找不到 manifest 文件：${manifestPath}`);
  }

  const manifest = readJson(absolutePath);
  const documents = Array.isArray(manifest)
    ? manifest
    : Array.isArray(manifest.documents)
      ? manifest.documents
      : null;

  if (!documents) {
    throw new Error('manifest 必须是数组，或包含 documents 数组');
  }

  return {
    path: absolutePath,
    dir: path.dirname(absolutePath),
    documents,
  };
}

function resolveEntry(entry, baseDir) {
  const sourcePath = normalizePath(entry.source, baseDir);
  if (!sourcePath) {
    throw new Error('缺少 source 字段');
  }

  const outputDir = normalizePath(entry.outputDir || path.dirname(sourcePath), baseDir);
  const baseName = sanitizeFileStem(entry.baseName || path.basename(sourcePath, path.extname(sourcePath)));
  const backupDirName = entry.backupDirName || entry.archiveDir || 'backup';

  return {
    sourcePath,
    outputDir,
    baseName,
    backupDirName,
  };
}

async function generateBundle(entry) {
  const { sourcePath, outputDir, baseName, backupDirName = 'backup' } = entry;

  if (!fs.existsSync(sourcePath)) {
    throw new Error(`找不到源文件：${sourcePath}`);
  }

  ensureDir(outputDir);

  const mdText = fs.readFileSync(sourcePath, 'utf8');
  const version = parseVersionFromText(mdText) || 'v0.1';
  const archived = archiveOldSnapshots(outputDir, baseName, backupDirName);

  const mdName = `${baseName}_${version}.md`;
  const mdSnapshotPath = path.join(outputDir, mdName);

  fs.copyFileSync(sourcePath, mdSnapshotPath);

  return {
    sourcePath,
    outputDir,
    baseName,
    version,
    archived,
    mdSnapshotPath,
  };
}

module.exports = {
  archiveOldSnapshots,
  ensureDir,
  generateBundle,
  loadManifestEntries,
  loadProfile,
  normalizePath,
  parseCliArgs,
  parseVersionFromText,
  readVersionFromMd,
  replaceTokens,
  resolveEntry,
  sanitizeFileStem,
  todayIso,
};
