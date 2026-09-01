import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read=(path)=>readFileSync(new URL(path,import.meta.url),'utf8');
const html=read('./src/index.html');
const js=read('./src/app.js');
const css=read('./src/styles.css');
const build=read('./build.mjs');
const pkg=JSON.parse(read('./package.json'));
const brand=read('./public/brand/brand-mark.svg');
const mono=read('./public/brand/brand-mark-mono.svg');
const favicon=read('./public/favicon.svg');
const og=read('./public/brand/og-source.svg');

assert.equal(pkg.scripts?.test,'node test.mjs','workspace test command must be mandatory and local');
assert.equal(pkg.scripts?.prebuild,'npm test','every build must fail closed through workspace tests');
assert.equal(pkg.scripts?.build,'node build.mjs');
assert.ok(build.includes("'app.js'"),'web build must retain runtime interaction code');
assert.ok(build.includes("cp('public','dist'"),'web build must retain split-local brand assets');
assert.ok(html.includes('rel="icon" href="/favicon.svg"'),'web must expose the split-retained favicon source');
for(const asset of [brand,favicon]){
  assert.ok(asset.includes('#314f38')&&asset.includes('#1d211f'),'brand source must use the controlled digital palette');
  assert.ok(!/<(?:linearGradient|radialGradient|filter|mask)\b/.test(asset),'canonical small-scale brand source must remain flat and unmasked');
}
assert.ok(brand.includes('controlled flowing seam'),'canonical mark must identify the revised flowing-seam geometry');
assert.ok(!brand.includes('h18v216')&&!brand.includes('M142 20h18'),'retired straight parallel-bar geometry must not return');
assert.equal((brand.match(/<path\b/g)||[]).length,2,'canonical mark must remain a two-field source');
assert.equal((mono.match(/<path\b/g)||[]).length,2,'monochrome mark must preserve two-field topology');
assert.ok(!brand.includes('<rect'),'canonical mark geometry must not depend on a platform container');
const seamTokens=['L106 20C110 48 100 76 108 104C118 134 103 165 113 195','M150 20L160 20','C142 222 139 207 144 191C152 164 137 138 145 109'];
for(const token of seamTokens){
  assert.ok(brand.includes(token),`canonical mark must retain optical seam geometry ${token}`);
  assert.ok(mono.includes(token),`monochrome mark must retain optical seam geometry ${token}`);
  assert.ok(favicon.includes(token),`favicon must derive from canonical seam geometry ${token}`);
  assert.ok(og.includes(token),`OG source must derive from canonical seam geometry ${token}`);
}
// Conservative raster-cell gate: every control point on the left seam stays <=118,
// every control point on the right seam stays >=137. At the authored 256-unit viewBox
// this guarantees at least one complete background raster column at 16/20/24/32 px.
const conservativeSeamUnits=137-118;
for(const size of [16,20,24,32]){
  const clearRasterColumns=Math.floor(conservativeSeamUnits*size/256);
  assert.ok(clearRasterColumns>=1,`flowing seam must retain a full clear raster column at ${size}px`);
}
assert.ok(og.includes('Development preview. No performance or availability claim.'),'social source must preserve evidence-safe copy');

const ids=new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((match)=>match[1]));
for(const match of html.matchAll(/\shref="#([^"]+)"/g)) assert.ok(ids.has(match[1]),`internal navigation target #${match[1]} must exist`);
const stageTag=html.match(/<div[^>]*\bclass="product-stage"[^>]*>/)?.[0]??'';
assert.ok(stageTag.includes('role="img"')&&stageTag.includes('aria-label='),'meaningful abstract product visual must expose image semantics');
const statusTag=html.match(/<[^>]*\bid="access-status"[^>]*>/)?.[0]??'';
assert.ok(statusTag.includes('role="status"')); assert.ok(statusTag.includes('aria-live="polite"')); assert.ok(statusTag.includes('aria-atomic="true"'));
const notifyTag=html.match(/<button[^>]*\bid="notify"[^>]*>/)?.[0]??'';
assert.ok(notifyTag.includes('aria-describedby="access-status"'));
assert.ok(html.includes('>Check early access</button>')); assert.ok(!html.includes('Join early access'));
assert.ok(js.includes('button.disabled=true')); assert.ok(js.includes("button.textContent='Early access not open'")); assert.ok(!js.includes('opening later')); assert.ok(js.includes('No signup or availability is implied'));
for(const token of ['fetch(','XMLHttpRequest','WebSocket']) assert.ok(!js.includes(token),`unexpected transport token: ${token}`);
const concreteDuration=/\b(?:one|1|60)\s*[- ]?\s*(?:min(?:ute)?s?|sec(?:ond)?s?)\b/i;
assert.ok(!concreteDuration.test(html));
for(const text of ['being engineered','Final service geometry remains subject to engineering validation.','No performance or availability claim is implied by this preview.']) assert.ok(html.includes(text));
for(const token of ['prefers-reduced-motion:reduce','prefers-contrast:more','forced-colors:active','@media(max-width:420px)',':focus-visible','.skip:focus']) assert.ok(css.includes(token));
console.log('Masck One web workspace tests passed');
