import { chromium } from 'playwright';

const URL='https://masck-one-final.vercel.app/';
const browser=await chromium.launch({headless:true});
try{
  const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  const page=await context.newPage();
  for(let i=0;i<35;i++){
    await page.goto(URL,{waitUntil:'domcontentloaded',timeout:45000});
    if(await page.locator('[data-use-journey18][data-version="v18"]').count()) break;
    if(i===34) throw new Error('Prompt 18 production deployment did not appear');
    await page.waitForTimeout(5000);
  }
  const stages=['prepare','wear','choose','clean','remove','service','recharge'];
  for(const key of stages){
    const article=page.locator(`[data-j18-mobile-stage="${key}"]`);
    await article.scrollIntoViewIfNeeded();
    await page.waitForTimeout(120);
    const spans=article.locator('.j18m-action span');
    const boxes=await spans.evaluateAll(nodes=>nodes.map(node=>{
      const r=node.getBoundingClientRect();
      const cs=getComputedStyle(node);
      return {text:node.textContent?.trim()||'',left:r.left,right:r.right,top:r.top,bottom:r.bottom,display:cs.display,visibility:cs.visibility,opacity:parseFloat(cs.opacity)};
    }));
    for(const box of boxes){
      if(box.display==='none'||box.visibility==='hidden'||box.opacity===0) continue;
      if(box.left<4||box.right>386) throw new Error(`mobile action label clipped at ${key}: ${JSON.stringify(box)}`);
      if(box.top<0||box.bottom>844) throw new Error(`mobile action label outside viewport at ${key}: ${JSON.stringify(box)}`);
    }
  }
  await context.close();
}finally{
  await browser.close();
}
