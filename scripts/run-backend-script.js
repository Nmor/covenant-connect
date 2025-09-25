#!/usr/bin/env node

const { existsSync } = require('fs');
const { join } = require('path');
const { spawnSync } = require('child_process');

const args = process.argv.slice(2);
const [scriptName, ...rest] = args;
const skipIfMissing = rest.includes('--skip-if-missing');
const forwardedArgs = rest.filter((arg) => arg !== '--skip-if-missing');

if (!scriptName) {
  console.error('Error: expected a backend script name as the first argument.');
  process.exit(1);
}

const workspaceName = '@covenant-connect/backend';
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

const { npm_execpath: npmExecPath, npm_node_execpath: nodeExecPath, npm_config_user_agent: userAgent } = process.env;

function detectPackageManager(execPath, ua) {
  const source = execPath || ua || '';
  if (/pnpm/i.test(source)) {
    return 'pnpm';
  }
  if (/yarn/i.test(source)) {
    return 'yarn';
  }
  return 'npm';
}

const packageManager = detectPackageManager(npmExecPath, userAgent);

let command;
let commandArgs;

if (npmExecPath && nodeExecPath) {
  command = nodeExecPath;
  commandArgs = [npmExecPath];
} else {
  command = packageManager;
  commandArgs = [];
}

if (packageManager === 'pnpm') {
  commandArgs.push('--filter', workspaceName, 'run', scriptName, ...forwardedArgs);
} else if (packageManager === 'yarn') {
  commandArgs.push('workspace', workspaceName, 'run', scriptName, ...forwardedArgs);
} else {
  commandArgs.push('--workspace', workspaceName, 'run', scriptName, ...forwardedArgs);
}

const result = spawnSync(command, commandArgs, {
  stdio: 'inherit',
  env: process.env,
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 0);
