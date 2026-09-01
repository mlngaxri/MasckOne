import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read=(path)=>readFileSync(new URL(path,import.meta.url),'utf8');
const html=read('./src/index.html');
const js=read('./src/app.js');
const css=read('./src/styles.css');
const build=read('./build.mjs');
const pkg=JSON.parse(read('./package.json'));

assert.equal(pkg.scripts?.test,'node test.mjs','workspace test command must be mandatory and local');
assert.equal(pkg.scripts?.prebuild,'npm test','every build must fail closed through workspace tests');
assert.equal(pkg.scripts?.build,'node build.mjs');
assert.ok(build.includes("'app.js'"),'app build must retain runtime interaction code');

const homeTag=html.match(/<section[^>]*\bid="home"[^>]*>/)?.[0]??'';
assert.ok(homeTag.includes('data-state-source="simulated"'),'app state must remain explicitly simulated');
assert.ok(homeTag.includes('data-device-transport="none"'),'unbound prototype must declare no device transport');
assert.ok(html.includes('Simulated device state, not live telemetry'));
assert.ok(html.includes('Preview only. No device command is sent.'));
for(const forbidden of ['Device Ready','System standing by']) assert.ok(!html.includes(forbidden),`hardware-ready copy is forbidden without telemetry: ${forbidden}`);

const liveTag=html.match(/<[^>]*\bid="simulation-status"[^>]*>/)?.[0]??'';
assert.ok(liveTag.includes('role="status"'),'simulation feedback must be a pre-existing live status region');
assert.ok(liveTag.includes('aria-live="polite"'));
assert.ok(liveTag.includes('aria-atomic="true"'));
const previewTag=html.match(/<button[^>]*\bid="preview-cleanse"[^>]*>/)?.[0]??'';
assert.ok(previewTag.includes('aria-controls="simulation-status"'));
assert.ok(js.includes('preview.disabled=true'),'preview action must settle deterministically');
assert.ok(js.includes('No device command was sent'),'runtime feedback must preserve simulation boundary');
assert.ok(!/<button[^>]*aria-label="Device settings"/i.test(html),'unavailable settings must not masquerade as an interactive control');
assert.ok(html.includes('Device settings are unavailable in this interaction prototype.'));
for(const token of ['fetch(','XMLHttpRequest','WebSocket','navigator.bluetooth','BluetoothRemoteGATT']) assert.ok(!js.includes(token),`unexpected device/network transport token: ${token}`);

const ids=new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((match)=>match[1]));
for(const match of html.matchAll(/\shref="#([^"]+)"/g)){
  assert.ok(ids.has(match[1]),`internal navigation target #${match[1]} must exist`);
}
assert.ok(js.includes('aria-current'));
assert.ok(js.includes('hashchange'));

for(const token of ['prefers-reduced-motion:reduce','prefers-contrast:more','forced-colors:active','safe-area-inset-bottom','@media(max-width:340px)',':focus-visible','.sr-only']){
  assert.ok(css.includes(token),`missing app accessibility fallback: ${token}`);
}

console.log('Masck One app workspace tests passed');
