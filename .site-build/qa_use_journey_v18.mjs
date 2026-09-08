import { chromium } from 'playwright';
import fs from 'node:fs';

const URL='https://masck-one-final.vercel.app/';
const OUT='/tmp/masck-p18-qa';
const labels=['PREPARE','WEAR','CHOOSE','CLEAN','REMOVE','SERVICE','RECHARGE'];
const keys=['prepare','wear','choose','clean','remove','service','recharge'];
fs.mkdirSync(OUT,{recursive:true});

async function waitForDeployment(page){
  for(let i=0;i<35;i++){
    await page.goto(URL,{waitUntil:'domcontentloaded',timeout:45000});
    if(await page.locator('[data-use-journey18][data-version="v18"]').count()) return;
    await page.waitForTimeout(5000);
  }
  throw new Error('Prompt 18 production deployment did not appear');
}

async function ensureImageLoaded(locator,label){
  await locator.evaluate((img,label)=>new Promise((resolve,reject)=>{
    const done=()=>img.naturalWidth>0&&img.naturalHeight>0;
    if(img.complete){
      if(done()) resolve(true); else reject(new Error(`${label} image completed without pixels: ${img.currentSrc||img.src}`));
      return;
    }
    const timer=setTimeout(()=>reject(new Error(`${label} image load timeout: ${img.currentSrc||img.src}`)),12000);
    img.addEventListener('load',()=>{clearTimeout(timer);done()?resolve(true):reject(new Error(`${label} image loaded without pixels`));},{once:true});
    img.addEventListener('error',()=>{clearTimeout(timer);reject(new Error(`${label} image failed: ${img.currentSrc||img.src}`));},{once:true});
  }),label);
}

async function waitForDesktopState(page,key){
  await page.waitForFunction((key)=>{
    const gesture=document.querySelector(`.journey18-desktop [data-j18-gesture="${key}"]`);
    const product=document.querySelector('.journey18-desktop .j18-product.active');
    if(!gesture||!product) return false;
    return parseFloat(getComputedStyle(gesture).opacity)>=0.98 && parseFloat(getComputedStyle(product).opacity)>=0.98;
  },key,{timeout:2500});
}

async function desktopQA(browser){
  const context=await browser.newContext({viewport:{width:1440,height:1000}});
  const page=await context.newPage();
  await waitForDeployment(page);
  const chapter=page.locator('[data-use-journey18]');
  const dims=await chapter.evaluate(el=>({top:scrollY+el.getBoundingClientRect().top,travel:el.offsetHeight-innerHeight,height:el.offsetHeight,viewport:innerHeight}));
  if(dims.travel<=dims.viewport) throw new Error('desktop journey has insufficient scroll travel');
  if(await page.locator('.journey18-desktop [data-j18-step]').count()!==7) throw new Error('desktop stage count mismatch');
  if(await page.locator('.j18-visual button').count()!==0) throw new Error('fake physical button found in product visual');
  const summary=[];
  for(let i=0;i<labels.length;i++){
    const y=dims.top+dims.travel*(i/(labels.length-1));
    await page.evaluate(y=>scrollTo(0,y),y);
    await page.waitForTimeout(80);
    const active=await chapter.getAttribute('data-active-index');
    if(active!==String(i)) throw new Error(`desktop active stage mismatch ${i}: ${active}`);
    const label=(await page.locator('[data-j18-label]').textContent()||'').trim();
    if(label!==labels[i]) throw new Error(`desktop label mismatch ${i}: ${label}`);
    await waitForDesktopState(page,keys[i]);
    const gesture=page.locator(`.journey18-desktop [data-j18-gesture="${keys[i]}"]`);
    const opacity=parseFloat(await gesture.evaluate(el=>getComputedStyle(el).opacity));
    if(opacity<0.98) throw new Error(`desktop gesture did not settle ${keys[i]} opacity=${opacity}`);
    const product=page.locator('.journey18-desktop .j18-product.active');
    await ensureImageLoaded(product,`desktop ${keys[i]}`);
    const image=await product.evaluate(img=>({naturalWidth:img.naturalWidth,naturalHeight:img.naturalHeight,width:img.getBoundingClientRect().width,opacity:getComputedStyle(img).opacity,src:img.currentSrc||img.src}));
    if(image.naturalWidth<1000||image.naturalHeight<1000||image.width<500||parseFloat(image.opacity)<0.98) throw new Error(`desktop product weak at ${keys[i]} ${JSON.stringify(image)}`);
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
    if(overflow>2) throw new Error(`desktop horizontal overflow ${overflow}`);
    await page.screenshot({path:`${OUT}/desktop-${String(i+1).padStart(2,'0')}-${keys[i]}.png`,fullPage:false});
    summary.push({stage:keys[i],label,image,gestureOpacity:opacity});
  }
  const serviceButton=page.locator('[data-j18-step="5"]');
  await serviceButton.click();
  await page.waitForFunction(()=>document.querySelector('[data-use-journey18]')?.dataset.activeIndex==='5',null,{timeout:2500});
  await waitForDesktopState(page,'service');
  if(await chapter.getAttribute('data-active-index')!=='5') throw new Error('desktop timeline click did not select SERVICE');
  fs.writeFileSync(`${OUT}/desktop-summary.json`,JSON.stringify(summary,null,2));
  await context.close();
}

async function mobileQA(browser){
  const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  const page=await context.newPage();
  await waitForDeployment(page);
  if(await page.locator('.journey18-mobile-state').count()!==7) throw new Error('mobile stage count mismatch');
  const displays=await page.evaluate(()=>({desktop:getComputedStyle(document.querySelector('.journey18-desktop')).display,mobile:getComputedStyle(document.querySelector('.journey18-mobile')).display}));
  if(displays.desktop!=='none'||displays.mobile==='none') throw new Error(`mobile layout mode wrong ${JSON.stringify(displays)}`);
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
  if(overflow>2) throw new Error(`mobile horizontal overflow ${overflow}`);
  let lastTop=-Infinity;
  const summary=[];
  for(let i=0;i<keys.length;i++){
    const article=page.locator(`[data-j18-mobile-stage="${keys[i]}"]`);
    const docTop=await article.evaluate(el=>scrollY+el.getBoundingClientRect().top);
    if(docTop<=lastTop) throw new Error(`mobile vertical order failed at ${keys[i]}`);
    lastTop=docTop;
    await article.scrollIntoViewIfNeeded();
    await page.waitForTimeout(120);
    const img=article.locator('img');
    await ensureImageLoaded(img,`mobile ${keys[i]}`);
    const image=await img.evaluate(el=>({naturalWidth:el.naturalWidth,width:el.getBoundingClientRect().width,height:el.getBoundingClientRect().height,src:el.currentSrc||el.src}));
    if(image.naturalWidth<1000||image.width<360) throw new Error(`mobile product too small at ${keys[i]} ${JSON.stringify(image)}`);
    const label=(await article.locator('h3').textContent()||'').trim();
    if(label!==labels[i]) throw new Error(`mobile label mismatch ${keys[i]}: ${label}`);
    await page.screenshot({path:`${OUT}/mobile-${String(i+1).padStart(2,'0')}-${keys[i]}.png`,fullPage:false});
    summary.push({stage:keys[i],label,image});
  }
  fs.writeFileSync(`${OUT}/mobile-summary.json`,JSON.stringify(summary,null,2));
  await context.close();
}

async function reducedMotionQA(browser){
  const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  const page=await context.newPage();
  await waitForDeployment(page);
  const chapter=page.locator('[data-use-journey18]');
  const dims=await chapter.evaluate(el=>({top:scrollY+el.getBoundingClientRect().top,travel:el.offsetHeight-innerHeight}));
  await page.evaluate(y=>scrollTo(0,y),dims.top+dims.travel*.5);
  await page.waitForTimeout(100);
  if(await chapter.getAttribute('data-active-index')!=='3') throw new Error('reduced-motion CLEAN selection failed');
  const product=page.locator('.journey18-desktop .j18-product.active');
  await ensureImageLoaded(product,'reduced motion clean');
  const anim=await page.locator('.j18-cycle-ring').evaluate(el=>getComputedStyle(el,'::before').animationName);
  if(anim!=='none') throw new Error(`reduced-motion cycle animation still active: ${anim}`);
  await page.screenshot({path:`${OUT}/reduced-motion-clean.png`,fullPage:false});
  await context.close();
}

const browser=await chromium.launch({headless:true});
try{
  await desktopQA(browser);
  await mobileQA(browser);
  await reducedMotionQA(browser);
}finally{
  await browser.close();
}
