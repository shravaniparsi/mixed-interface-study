// Prepared single-tab browser checkpoint, requiring isolated runtime controls.
import assert from 'node:assert/strict';
import {sameState} from './maxun_serializer_v1.mjs';

export async function captureBrowserState(context, page, origin) {
  assert.equal(new URL(page.url()).origin, origin);
  assert.equal(context.pages().length, 1, 'Unmapped additional browser tab');
  assert.equal(context.serviceWorkers().length, 0, 'Uncopyable service-worker state');
  const session = await page.evaluate(async () => {
    if (typeof indexedDB.databases !== 'function') throw new Error('Cannot inventory IndexedDB');
    if ((await indexedDB.databases()).length) throw new Error('IndexedDB requires separate qualified snapshot');
    if ((await caches.keys()).length) throw new Error('CacheStorage requires separate qualified snapshot');
    return Object.fromEntries(Object.keys(sessionStorage).sort().map(key => [key, sessionStorage.getItem(key)]));
  });
  return {origin, session, storage: await context.storageState(),
    runtimeQualified:false, coverage:'cookies, localStorage, single-tab sessionStorage; IndexedDB/cache/workers must be absent'};
}

export async function restoreBrowserState(browser, fixture, options) {
  assert.equal(new URL(fixture.origin).origin, fixture.origin);
  // This helper never installs a recurring init script. Doing so would silently
  // restore old session values again on later native navigation.
  const context = await browser.newContext({...options, storageState: fixture.storage, serviceWorkers:'block'});
  try {
    const page = await context.newPage();
    const bootstrap = fixture.origin + '/__study_browser_restore__';
    const handler = route => route.fulfill({status:200,contentType:'text/html',body:'<!doctype html><title>State restoration</title>'});
    await page.route(bootstrap, handler);
    await page.goto(bootstrap, {waitUntil:'domcontentloaded'});
    await page.evaluate(session => {
      sessionStorage.clear();
      for (const [key,value] of Object.entries(session)) {
        if (typeof value !== 'string') throw new Error('Invalid session value');
        sessionStorage.setItem(key,value);
      }
    }, fixture.session);
    await page.unroute(bootstrap, handler);
    const restored = await captureBrowserState(context,page,fixture.origin);
    assert.ok(sameState(restored.storage,fixture.storage), 'Browser cookies/localStorage changed during restoration');
    assert.ok(sameState(restored.session,fixture.session), 'Browser sessionStorage differs');
    return {context,page,restored};
  } catch (error) {
    await context.close();
    throw error;
  }
}
