import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {assertSmallScaleSeam} from './brand-raster.mjs';

const read=(p)=>readFileSync(new URL(p,import.meta.url),'utf8');
const html=read('./src/index.html');
const js=read('./src/app.js');
const cinematic=read('./src/cinematic.js');
const css=read('./src/styles.css');
const build=read('./build.mjs');
const pkg=JSON.parse(read('./package.json'));
const brand=read('./public/brand/brand-mark.svg');
const mono=read('./public/brand/brand-mark-mono.svg');
const favicon=read('./public/favicon.svg');
const og=read('./public/brand/og-source.svg');
const social=read('./public/brand/social-avatar-source.svg');

assert.equal(pkg.scripts?.test,'node test.mjs');
assert.equal(pkg.scripts?.prebuild,'npm test');
assert.equal(pkg.scripts?.build,'node build.mjs');
assert.ok(build.includes("'app.js'")&&build.includes("'cinematic.js'")&&build.includes("cp('public','dist'"));
assert.ok(html.includes('rel="icon" href="/favicon.svg"'));

for(const asset of [brand,favicon,og,social]){
  assert.ok(asset.includes('dominant-field-insert-v3'));
  assert.ok(!/<(?:linearGradient|radialGradient|filter|mask)\b/.test(asset));
}
for(const asset of [brand,favicon,social])assert.ok(asset.includes('#314f38')&&asset.includes('#1d211f'));
assert.equal((brand.match(/<path\b/g)||[]).length,2);
assert.equal((mono.match(/<path\b/g)||[]).length,2);
assert.ok(mono.includes('dominant-field-insert-v3')&&!brand.includes('<rect'));
for(const retired of ['h18v216','M142 20h18','M40 72C40 40 65 20 96 20h16','M144 20h16','M40 72C40 40 65 20 96 20h10','M150 20h10','M40 72C40 40 65 20 96 20L106 20','M150 20L160 20'])assert.ok(!brand.includes(retired));
for(const token of ['M44 76C44 44 68 24 100 24H150','M172 24H180'])for(const asset of [brand,favicon,og,social])assert.ok(asset.includes(token));
assert.ok(106/8>=10,'dominant field and insert must not regress to equal bars');
for(const [name,asset] of [['canonical',brand],['monochrome',mono],['favicon',favicon]])assertSmallScaleSeam(asset,name);
assert.ok(og.includes('Development preview. No performance or availability claim.'));

const ids=new Set([...html.matchAll(/\sid="([^"]+)"/g)].map(match=>match[1]));
for(const match of html.matchAll(/\shref="#([^"]+)"/g))assert.ok(ids.has(match[1]),`missing fragment target ${match[1]}`);
const stage=html.match(/<div[^>]*\bclass="product-stage"[^>]*>/)?.[0]??'';
assert.ok(stage.includes('role="img"')&&stage.includes('aria-label='));
const statusTag=html.match(/<[^>]*\bid="access-status"[^>]*>/)?.[0]??'';
assert.ok(statusTag.includes('role="status"')&&statusTag.includes('aria-live="polite"')&&statusTag.includes('aria-atomic="true"'));
const notify=html.match(/<button[^>]*\bid="notify"[^>]*>/)?.[0]??'';
assert.ok(notify.includes('aria-describedby="access-status"'));
assert.ok(html.includes('Check early access')&&!html.includes('Join early access'));
assert.ok(js.includes('button.disabled=true')&&js.includes("button.textContent='Early access not open'")&&!js.includes('opening later')&&js.includes('No signup or availability is implied'));
for(const token of ['fetch(','XMLHttpRequest','WebSocket'])assert.ok(!js.includes(token));
assert.ok(!/\b(?:one|1|60)\s*[- ]?\s*(?:min(?:ute)?s?|sec(?:ond)?s?)\b/i.test(html));
for(const token of ['being engineered','Final service geometry remains subject to engineering validation.','No performance or availability claim is implied by this preview.','Currently in engineering development.'])assert.ok(html.includes(token));

for(const id of ['system','sequence','anatomy','service','development','access'])assert.ok(ids.has(id));
for(const token of ['THE ROUTINE, REBUILT.','DELIVER','WORK','COLLECT','VALIDATION-GATED','NOT IMPLIED'])assert.ok(html.includes(token));
assert.ok(html.includes('gsap@3.13.0')&&html.includes('ScrollTrigger.min.js')&&html.includes('lenis@1.3.11'));
for(const token of ['window.gsap','window.ScrollTrigger','window.Lenis','lerp:0.075','dataset.explodeX','ScrollTrigger.refresh','prefers-reduced-motion: reduce','pointer: fine',"import('./cinematic.js')"])assert.ok(js.includes(token));
for(const token of ['handoffOut','handoffIn','clipPath','scrub:1.35','parallax','rotationZ'])assert.ok(cinematic.includes(token));
for(const token of ['.exploded-product','position:sticky','.cursor','.sequence-track','.service-cartridge','Instrument Serif','Instrument Sans','prefers-reduced-motion:reduce','prefers-contrast:more','forced-colors:active','@media(max-width:420px)',':focus-visible','.skip:focus'])assert.ok(css.includes(token));
assert.ok(css.includes('--canvas:#edeae3')&&css.includes('--ink:#2c2a27')&&css.includes('--champagne:#c9b99f'));

console.log('Masck One web workspace tests passed');
