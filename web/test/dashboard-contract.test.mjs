import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

test('dashboard contract keeps the import, analytics, and export surfaces', async () => {
  const source = await readFile(new URL('../src/app.tsx', import.meta.url), 'utf8');
  for (const route of ['/api/v1/summary', '/api/v1/costs', '/api/v1/imports', 'Export costs']) {
    assert.match(source, new RegExp(route.replaceAll('/', '\\/')));
  }
  assert.match(source, /role="alert"/);
  assert.match(source, /accept="\.csv,text\/csv"/);
});
