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
assert.ok(build.includes("'app.js'"),'web build must retain runtime interaction code');

const ids=new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((match)=>match[1]));
for(const match of html.matchAll(/\shref="#([^"]+)"/g)){
  assert.ok(ids.has(match[1]),`internal navigation target #${match[1]} must exist`);
}

const statusTag=html.match(/<[^>]*\bid="access-status"[^>]*>/)?.[0]??'';
assert.ok(statusTag.includes('role="status"'),'early-access status must be a live status region before mutation');
assert.ok(statusTag.includes('aria-live="polite"'));
assert.ok(statusTag.includes('aria-atomic="true"'));
const notifyTag=html.match(/<button[^>]*\bid="notify"[^>]*>/)?.[0]??'';
assert.ok(notifyTag.includes('aria-describedby="access-status"'));
assert.ok(html.includes('>Check early access</button>'),'CTA must describe a status check, not imply a signup action');
assert.ok(!html.includes('Join early access'),'public CTA must not imply a join path that does not exist');
assert.ok(js.includes('button.disabled=true'),'early-access action must fail closed after activation');
assert.ok(js.includes("button.textContent='Early access not open'"),'post-action copy must not imply future availability');
assert.ok(!js.includes('opening later'),'runtime copy must not imply an unverified availability timeline');
assert.ok(js.includes('No signup or availability is implied'),'feedback must not imply signup or availability');
for(const token of ['fetch(','XMLHttpRequest','WebSocket']) assert.ok(!js.includes(token),`unexpected transport token: ${token}`);

const concreteDuration=/\b(?:one|1|60)\s*[- ]?\s*(?:min(?:ute)?s?|sec(?:ond)?s?)\b/i;
assert.ok(!concreteDuration.test(html),'public web must not publish an unverified concrete cycle duration');
for(const text of ['being engineered','Final service geometry remains subject to engineering validation.','No performance or availability claim is implied by this preview.']){
  assert.ok(html.includes(text),`missing development evidence boundary: ${text}`);
}

for(const token of ['prefers-reduced-motion:reduce','prefers-contrast:more','forced-colors:active','@media(max-width:420px)',':focus-visible','.skip:focus']){
  assert.ok(css.includes(token),`missing web accessibility fallback: ${token}`);
}

console.log('Masck One web workspace tests passed');
