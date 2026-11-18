// Prepared ordinary-control browser actions; no dispatch or scientific inputs.
import assert from 'node:assert/strict';
import {crawlEditBody, sameState} from './maxun_serializer_v1.mjs';

export const ORDINARY = Object.freeze({
  name:'Study crawl robot', url:'http://localhost:8765/ordinary',
  crawlConfig:{mode:'domain',limit:50,maxDepth:3,includePaths:[],excludePaths:[],
    useSitemap:true,followLinks:true,respectRobots:true}, formats:['markdown'],
});
export const EDIT = Object.freeze({field:'name',value:'Study crawl robot edited'});

export async function nativeLogin(page, frontend, actor) {
  await page.goto(frontend + '/login', {waitUntil:'domcontentloaded'});
  await page.getByRole('textbox', {name:/email/i}).fill(actor.email);
  await page.locator('input[type="password"]').fill(actor.password);
  await page.locator('form').getByRole('button', {name:/log\s*in|sign\s*in/i}).click();
  await page.waitForURL(url => url.origin === frontend && url.pathname !== '/login');
}

async function markdownOnly(page) {
  await page.getByRole('combobox', {name:'Output formats',exact:true}).click();
  const options = page.getByRole('option');
  const count = await options.count();
  assert.ok(count > 0, 'Missing native format choices');
  let markdown = false;
  for (let i=0;i<count;i++) {
    const option = options.nth(i);
    const value = await option.getAttribute('data-value');
    const selected = await option.getAttribute('aria-selected');
    assert.ok(value !== null && ['true','false'].includes(selected), 'Unmapped native format option');
    const wanted = value === 'markdown';
    if (wanted) markdown = true;
    if ((selected === 'true') !== wanted) await option.click();
  }
  assert.ok(markdown, 'Markdown choice unavailable');
  await page.keyboard.press('Escape');
}

export async function nativeCreate(page, frontend, backend, record) {
  await page.goto(frontend + '/robots/create', {waitUntil:'domcontentloaded'});
  await page.getByRole('tab', {name:/crawl/i}).click();
  const panel = page.locator('[role="tabpanel"]:visible');
  await panel.getByRole('textbox', {name:'Starting page address',exact:true}).fill(ORDINARY.url);
  await panel.getByRole('textbox', {name:/^Name/}).fill(ORDINARY.name);
  await markdownOnly(page);
  const endpoint = backend + '/storage/recordings/crawl';
  const [response] = await Promise.all([
    page.waitForResponse(r => r.url() === endpoint && r.request().method() === 'POST'),
    panel.getByRole('button', {name:'Create robot',exact:true}).click(),
  ]);
  const submitted = response.request().postDataJSON();
  const body = await response.json();
  await record({kind:'native_create',status:response.status(),submitted,response:body});
  assert.equal(response.status(),201);
  assert.ok(sameState(submitted,ORDINARY), 'Native producer body differs from frozen ordinary API body');
  assert.equal(typeof body.robot?.recording_meta?.id,'string');
  return body.robot.recording_meta.id;
}

export async function openNativeEdit(page, frontend, readback) {
  await page.goto(frontend + '/robots', {waitUntil:'domcontentloaded'});
  assert.equal(typeof readback.recording_meta.name,'string');
  const row = page.getByRole('row').filter({has:page.getByText(readback.recording_meta.name,{exact:true})});
  await row.first().waitFor({state:'visible'});
  assert.equal(await row.count(),1,'Target native table row must be unique');
  await row.getByRole('button',{name:'options',exact:true}).click();
  await page.getByRole('menuitem',{name:'Edit',exact:true}).click();
  await page.waitForURL(frontend + '/robots/' + readback.recording_meta.id + '/edit');
  await page.getByRole('textbox',{name:/name/i}).waitFor({state:'visible'});
}

export async function nativeEdit(page, backend, readback, record) {
  const expected = crawlEditBody(readback, EDIT.field, EDIT.value);
  await page.getByRole('textbox',{name:/name/i}).fill(EDIT.value);
  const endpoint = backend + '/storage/recordings/' + readback.recording_meta.id;
  const [response] = await Promise.all([
    page.waitForResponse(r => r.url() === endpoint && r.request().method() === 'PUT'),
    page.getByRole('button',{name:/save/i}).click(),
  ]);
  const submitted = response.request().postDataJSON();
  const body = await response.json();
  await record({kind:'native_edit',status:response.status(),submitted,expected,response:body});
  assert.ok(sameState(submitted,expected),'Native/API serializer parity failed');
  assert.equal(response.status(),200);
  // Caller must perform fresh API AND persisted-state readback. The update
  // response is not accepted as proof of persistence.
  return {submitted, runtimeQualified:false};
}
