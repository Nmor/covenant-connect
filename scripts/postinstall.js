const { existsSync } = require('fs');
const { spawnSync } = require('child_process');

const workspacePath = 'apps/backend/package.json';

if (!existsSync(workspacePath)) {
  console.log('Skipping backend prisma generate: workspace not present.');
  process.exit(0);
}

const result = spawnSync(
  'npm',
  ['run', 'prisma:generate', '--workspace=@covenant-connect/backend'],
  {
    stdio: 'inherit',
    shell: process.platform === 'win32'
  }
);

if (result.status !== 0) {
  process.exit(result.status ?? 1);
}
