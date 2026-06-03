import { strict as assert } from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { resolveApiBaseUrl } from './apiConfig';

assert.equal(
  resolveApiBaseUrl({
    hostname: '0.0.0.0',
    protocol: 'http:',
    port: '3000',
  }, 8003),
  '/api'
);

const aiProviderApiSource = readFileSync(
  join(process.cwd(), 'src/services/aiProviderAPI.ts'),
  'utf8'
);

if (!aiProviderApiSource.includes("'request'")) {
  throw new Error('AI provider API protocol union should include direct request mode.');
}

assert.equal(
  resolveApiBaseUrl({
    hostname: 'localhost',
    protocol: 'http:',
    port: '3000',
  }, 8003),
  '/api'
);
