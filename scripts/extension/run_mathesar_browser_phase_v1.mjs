import fs from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { parseArgs } from 'node:util';
import assert from 'node:assert/strict';
import { bootstrap, createOrdinary, continueOrdinary, monitorLocalRequests } from './mathesar_ordinary_browser_v1.mjs';

const { values: args } = parseArgs({ options: {
  phase: { type: 'string' }, out: { type: 'string' }, private: { type: 'string' },
} });
assert(['producer', 'warm', 'seed', 'native', 'api'].includes(args.phase));
const reportPath = `${args.out}/${args.phase}-browser.json`;
const privatePath = args.private;
const report = { phase: args.phase, status: 'failed' };
let browser;
let fixture;
let storage;
try {
  assert.equal(process.version, 'v20.20.2');
  const require = createRequire(import.meta.url);
  const modulePath = process.env.PLAYWRIGHT_MODULE_PATH;
  const { chromium } = require(modulePath);
  assert.equal(require(modulePath + '/package.json').version, '1.62.1');
  const executable = '/ms-playwright/chromium-1234/chrome-linux64/chrome';
  const executableHash = createHash('sha256').update(await fs.readFile(executable)).digest('hex');
  assert.equal(executableHash, '0b20b130e7edd9dd51873be867761295fe0cfad490c2b9a64f95bd3cfc08fa71');
  fixture = JSON.parse(await fs.readFile(`${privatePath}/fixture.json`, 'utf8'));
  browser = await chromium.launch({ headless: true, executablePath: executable,
    args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  report.browser_version = browser.version();
  report.executable_sha256 = executableHash;
  assert.equal(report.browser_version, '151.0.7922.34');
  const resumed = ['native', 'api'].includes(args.phase);
  storage = resumed ? JSON.parse(await fs.readFile(`${privatePath}/seed-storage.json`, 'utf8')) : undefined;
  const context = await browser.newContext({ locale: 'en-US', viewport: { width: 1280, height: 960 },
    ...(storage ? { storageState: storage } : {}) });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  page.setDefaultNavigationTimeout(30000);
  const monitor = monitorLocalRequests(page);
  report.external_requests = monitor.external;
  report.page_errors = monitor.pageErrors;
  if (!resumed) {
    report.bootstrap = await bootstrap(page, fixture.admin_password);
    report.producer = await createOrdinary(page, fixture.target_password, args.phase === 'producer');
    if (args.phase === 'warm') {
      report.continuation = await continueOrdinary(page, report.producer.target.id, true);
    }
    if (args.phase === 'seed') {
      await fs.writeFile(`${privatePath}/seed-storage.json`, JSON.stringify(await context.storageState()), { mode: 0o600 });
      await fs.writeFile(`${privatePath}/seed-target.json`, JSON.stringify(report.producer.target), { mode: 0o600 });
    }
  } else {
    const target = JSON.parse(await fs.readFile(`${privatePath}/seed-target.json`, 'utf8'));
    report.restored_storage_sha256 = createHash('sha256').update(JSON.stringify(storage)).digest('hex');
    report.continuation = await continueOrdinary(page, target.id, args.phase === 'native');
    assert.deepEqual(report.continuation.before, target);
  }
  monitor.verify();
  await page.screenshot({ path: `${args.out}/${args.phase}.png`, fullPage: true });
  await context.close();
  report.status = 'ordinary_phase_passed';
} catch (error) {
  // Detailed failures can include request values; retain them privately.
  await fs.writeFile(`${privatePath}/${args.phase}-error.txt`, String(error.stack ?? error), { mode: 0o600 });
  report.error_type = error.name;
  if (error.evidence) report.failure_evidence = error.evidence;
  let message = String(error.message);
  for (const value of [...Object.values(fixture ?? {}), ...(storage?.cookies ?? []).map((cookie) => cookie.value)]) {
    if (value) message = message.split(value).join('<private>');
  }
  report.failure_detail = message.slice(0, 6000);
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + '\n', { flag: 'wx' });
}
