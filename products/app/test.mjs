import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read=(path)=>readFileSync(new URL(path,import.meta.url),'utf8');
const html=read('./src/index.html');
const js=read('./src/app.js');
const css=read('./src/styles.css');
const build=read('./build.mjs');
const pkg=JSON.parse(read('./package.json'));
const brand=read('./assets/brand/brand-mark.svg');
const appIcon=read('./assets/brand/app-icon-source.svg');

assert.equal(pkg.scripts?.test,'node test.mjs'); assert.equal(pkg.scripts?.prebuild,'npm test'); assert.equal(pkg.scripts?.build,'node build.mjs');
assert.ok(build.includes("'app.js'")); assert.ok(build.includes("cp('assets','dist/assets'"),'app build must retain split-local brand assets');
assert.ok(appIcon.includes('viewBox="0 0 1024 1024"'),'app icon source must retain the 1024 square production canvas');
for(const asset of [brand,appIcon]){
  assert.ok(asset.includes('#314f38')&&asset.includes('#1d211f'),'brand source must use the controlled digital palette');
  assert.ok(!/<(?:linearGradient|radialGradient|filter|mask)\b/.test(asset),'icon source must remain flat and unmasked');
}
const homeTag=html.match(/<section[^>]*\bid="home"[^>]*>/)?.[0]??'';
assert.ok(homeTag.includes('data-state-source="simulated"')); assert.ok(homeTag.includes('data-device-transport="none"')); assert.ok(html.includes('Simulated device state, not live telemetry')); assert.ok(html.includes('Preview only. No device command is sent.'));
for(const forbidden of ['Device Ready','System standing by']) assert.ok(!html.includes(forbidden));
const liveTag=html.match(/<[^>]*\bid="simulation-status"[^>]*>/)?.[0]??''; assert.ok(liveTag.includes('role="status"')); assert.ok(liveTag.includes('aria-live="polite"')); assert.ok(liveTag.includes('aria-atomic="true"'));
const previewTag=html.match(/<button[^>]*\bid="preview-cleanse"[^>]*>/)?.[0]??''; assert.ok(previewTag.includes('aria-controls="simulation-status"')); assert.ok(js.includes('preview.disabled=true')); assert.ok(js.includes('No device command was sent'));
assert.ok(!/<button[^>]*aria-label="Device settings"/i.test(html)); assert.ok(!/class="settings-unavailable"[^>]*aria-describedby=/i.test(html)); assert.ok(html.includes('Device settings are unavailable in this interaction prototype.'));
for(const token of ['fetch(','XMLHttpRequest','WebSocket','navigator.bluetooth','BluetoothRemoteGATT']) assert.ok(!js.includes(token));
const ids=new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((match)=>match[1])); for(const match of html.matchAll(/\shref="#([^"]+)"/g)) assert.ok(ids.has(match[1]));
assert.ok(js.includes('aria-current')); assert.ok(js.includes('hashchange'));
for(const token of ['prefers-reduced-motion:reduce','prefers-contrast:more','forced-colors:active','safe-area-inset-bottom','@media(max-width:340px)',':focus-visible','.sr-only']) assert.ok(css.includes(token));
console.log('Masck One app workspace tests passed');
