const path = require('path');

process.env.TS_NODE_PROJECT = path.resolve(__dirname, '../tsconfig.json');
process.env.TS_NODE_TRANSPILE_ONLY = 'true';
process.env.TS_NODE_FILES = 'true';

require('ts-node/register');
require('tsconfig-paths/register');
require('reflect-metadata');
