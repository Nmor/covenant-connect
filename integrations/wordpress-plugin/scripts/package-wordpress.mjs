#!/usr/bin/env node
import { fileURLToPath } from 'url';
import path from 'path';
import os from 'os';
import { spawn } from 'child_process';
import {
  cp,
  mkdir,
  mkdtemp,
  readFile,
  rename,
  rm,
  stat
} from 'fs/promises';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const pluginRoot = path.resolve(__dirname, '..');
const distDir = path.join(pluginRoot, 'dist');
const buildDir = path.join(pluginRoot, 'build');
const assetFile = path.join(buildDir, 'index.js');

async function ensureBuildArtifacts() {
  try {
    await stat(assetFile);
  } catch (error) {
    throw new Error(
      'Missing build output. Run "pnpm --filter @covenant-connect/wordpress-plugin build" before packaging.'
    );
  }
}

async function readPluginVersion() {
  const pluginFile = path.join(pluginRoot, 'covenant-connect.php');
  const contents = await readFile(pluginFile, 'utf8');

  const headerMatch = contents.match(/Version:\s*([0-9.]+)/i);
  if (headerMatch && headerMatch[1]) {
    return headerMatch[1].trim();
  }

  const constantMatch = contents.match(/COVENANT_CONNECT_PLUGIN_VERSION',\s*'([^']+)'/);
  if (constantMatch && constantMatch[1]) {
    return constantMatch[1].trim();
  }

  return null;
}

const excludedRoots = new Set([
  'dist',
  'node_modules',
  'src',
  'scripts',
  'package.json',
  'pnpm-lock.yaml',
  'package-lock.json',
  'yarn.lock',
  '.gitignore'
]);

function shouldInclude(source) {
  const relative = path.relative(pluginRoot, source);
  if (!relative || relative.startsWith('..')) {
    return true;
  }

  const [rootSegment] = relative.split(path.sep);
  if (excludedRoots.has(rootSegment)) {
    return false;
  }

  return true;
}

function runZip(cwd, zipName, folder) {
  return new Promise((resolve, reject) => {
    const child = spawn('zip', ['-r', zipName, folder], {
      cwd,
      stdio: 'inherit'
    });

    child.on('error', reject);
    child.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`zip exited with status ${code}`));
      }
    });
  });
}

async function main() {
  await ensureBuildArtifacts();
  await mkdir(distDir, { recursive: true });

  const version = await readPluginVersion();
  const slug = 'covenant-connect';
  const zipName = version
    ? `covenant-connect-wordpress-v${version}.zip`
    : 'covenant-connect-wordpress.zip';

  const stagingRoot = await mkdtemp(path.join(os.tmpdir(), 'covenant-connect-plugin-'));
  const stagingPluginDir = path.join(stagingRoot, slug);

  try {
    await cp(pluginRoot, stagingPluginDir, {
      recursive: true,
      filter: (source) => shouldInclude(source)
    });

    const zipPath = path.join(distDir, zipName);
    await rm(zipPath, { force: true });

    console.log(`Creating ${zipName}...`);
    await runZip(stagingRoot, zipName, slug);

    await rename(path.join(stagingRoot, zipName), zipPath);
    console.log(`Plugin package created at ${zipPath}`);
  } finally {
    await rm(stagingRoot, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
