const { existsSync } = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const workspaceManifest = path.resolve(
  __dirname,
  '..',
  'apps/backend/package.json'
);

if (!existsSync(workspaceManifest)) {
  console.log('Skipping backend prisma generate: workspace not present.');
  process.exit(0);
}

const backendWorkspaceDir = path.dirname(workspaceManifest);

const npmExec = process.env.npm_execpath;

let command;
let args;

if (npmExec) {
  command = process.execPath;
  args = [npmExec, 'run', 'prisma:generate'];
} else {
  command = process.platform === 'win32' ? 'npm.cmd' : 'npm';
  args = ['run', 'prisma:generate'];
}

const result = spawnSync(command, args, {
  stdio: 'inherit',
  cwd: backendWorkspaceDir
});

if (result.error) {
  console.error(result.error);
}

if (result.status !== 0) {
  process.exit(result.status ?? 1);
}
