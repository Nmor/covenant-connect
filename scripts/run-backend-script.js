#!/usr/bin/env node

const { existsSync } = require('fs');
const { join } = require('path');
const { spawnSync } = require('child_process');

const args = process.argv.slice(2);
const [scriptName, ...rest] = args;
const skipIfMissing = rest.includes('--skip-if-missing');

if (!scriptName) {
  console.error('Error: expected a backend script name as the first argument.');
  process.exit(1);
}

const backendPath = join(process.cwd(), 'apps', 'backend');

if (!existsSync(backendPath)) {
  const message = 'Backend workspace not found at "apps/backend".';
  if (skipIfMissing) {
    console.log(`Skipping backend script "${scriptName}": ${message}`);
    process.exit(0);
  }

  console.error(`Cannot run backend script "${scriptName}": ${message}`);
  process.exit(1);
}

const result = spawnSync(
  'npm',
  ['--workspace', '@covenant-connect/backend', 'run', scriptName, ...rest.filter((arg) => arg !== '--skip-if-missing')],
  {
    stdio: 'inherit',
    env: process.env,
  }
);

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 0);
