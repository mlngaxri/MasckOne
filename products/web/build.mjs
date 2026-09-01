import { cp, mkdir, rm } from 'node:fs/promises';
await rm('dist',{recursive:true,force:true}); await mkdir('dist');
for (const f of ['index.html','styles.css','app.js']) await cp(`src/${f}`,`dist/${f}`);
await cp('public','dist',{recursive:true});
console.log('Masck One web build complete');