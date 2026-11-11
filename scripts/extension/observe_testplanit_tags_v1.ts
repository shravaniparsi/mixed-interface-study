// Installed into packages/mcp-server; uses actual SDK, HTTP and host persistence.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { registerCasesUpdate } from './src/tools/cases/update.js';
import { zenstack } from './src/api.js';

async function main() {
  const [version, output, fixturePath, host] = process.argv.slice(2);
  fs.mkdirSync(output, {recursive: true});
  const fixture = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
  const env = {apiUrl: 'http://127.0.0.1:3002', apiToken: fixture.token};
  const runFixture = (mode: string, dest: string, arg: string) => execFileSync('pnpm', ['exec', 'tsx', 'scripts/study_fixture_v1.ts', mode, dest, arg], {cwd: host, stdio: 'inherit', timeout: 60000});
  const server = new McpServer({name: 'study', version: '1'});
  registerCasesUpdate(server, {env});
  const client = new Client({name: 'study-observer', version: '1'});
  const [left, right] = InMemoryTransport.createLinkedPair();
  await server.connect(left);
  await client.connect(right);
  const advertised = await client.listTools();
  fs.writeFileSync(path.join(output, 'tools.json'), JSON.stringify(advertised, null, 2));
  for (const kind of ['replace', 'omit', 'clear', 'same']) {
    const prefix = path.join(output, kind);
    runFixture('create', prefix + '-fixture.json', fixturePath);
    const {caseId} = JSON.parse(fs.readFileSync(prefix + '-fixture.json', 'utf8'));
    runFixture('read', prefix + '-before.json', String(caseId));
    const args = kind === 'omit' ? {caseId, name: 'edited-' + version} : {caseId, tags: kind === 'clear' ? [] : [fixture.tags[kind === 'replace' ? 1 : 0].id]};
    const trace: any[] = [];
    const realFetch = globalThis.fetch;
    globalThis.fetch = async (url, init) => {
      if (!String(url).startsWith(env.apiUrl + '/')) throw new Error('Nonlocal request refused');
      const record: any = {url: String(url), method: init?.method ?? 'GET', body: init?.body ?? null};
      trace.push(record);
      try {
        const response = await realFetch(url, init);
        record.status = response.status;
        record.response = await response.clone().text();
        return response;
      } catch (e) { record.error = String(e); throw e; }
    };
    let result: any;
    try { result = await client.callTool({name: 'testplanit_cases_update', arguments: args}, undefined, {timeout: 60000}); }
    catch (e) { result = {transportError: String(e)}; }
    finally { globalThis.fetch = realFetch; }
    runFixture('read', prefix + '-after.json', String(caseId));
    let readback: any;
    try { readback = await zenstack('repositoryCases', 'findUnique', {where: {id: caseId}, include: {caseTags: {include: {tag: true}}}}, env); }
    catch (e) { readback = {error: String(e)}; }
    fs.writeFileSync(prefix + '-observation.json', JSON.stringify({version, kind, args, result, trace, readback}, null, 2));
  }
  await client.close();
  await server.close();
}
main().catch(e => { console.error(e); process.exitCode = 1; });
