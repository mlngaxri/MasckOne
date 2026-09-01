const button=document.querySelector('#notify');
const status=document.querySelector('#access-status');
button?.addEventListener('click',()=>{
  button.disabled=true;
  button.textContent='Early access not open';
  if(status) status.textContent='Early access is not open yet. No signup or availability is implied by this preview.';
});

const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const finePointer=window.matchMedia('(pointer: fine)').matches;
const desktop=window.matchMedia('(min-width: 861px)').matches;
const gsap=window.gsap;
const ScrollTrigger=window.ScrollTrigger;
const Lenis=window.Lenis;
const header=document.querySelector('[data-header]');
const menuToggle=document.querySelector('[data-menu-toggle]');
const menuPanel=document.querySelector('[data-menu-panel]');
const brandMark=header?.querySelector('.brand img');
let lenisInstance=null;

const clamp=(min,max,value)=>Math.min(max,Math.max(min,value));
const setHeaderState=()=>header?.classList.toggle('is-scrolled',window.scrollY>24);
setHeaderState();
window.addEventListener('scroll',setHeaderState,{passive:true});

const setMenuHeaderContrast=(open)=>{
  if(!header)return;
  header.style.color=open?'#edeae3':'';
  header.style.backgroundColor=open?'transparent':'';
  header.style.borderColor=open?'transparent':'';
  if(brandMark)brandMark.style.filter=open?'grayscale(1) brightness(0) invert(1)':'';
};

const setMenu=(open)=>{
  if(!menuToggle||!menuPanel)return;
  menuToggle.setAttribute('aria-expanded',String(open));
  menuPanel.setAttribute('aria-hidden',String(!open));
  document.body.classList.toggle('menu-open',open);
  setMenuHeaderContrast(open);
  if(open)lenisInstance?.stop();
  else lenisInstance?.start();
  if(gsap&&!reducedMotion){
    if(open){
      menuPanel.classList.add('is-open');
      gsap.fromTo(menuPanel,{clipPath:'inset(0 0 100% 0)',autoAlpha:0},{clipPath:'inset(0 0 0% 0)',autoAlpha:1,duration:.72,ease:'power4.inOut'});
      gsap.fromTo(menuPanel.querySelectorAll('nav a'),{y:46,opacity:0},{y:0,opacity:1,duration:.7,stagger:.055,delay:.18,ease:'power3.out'});
    }else{
      gsap.to(menuPanel,{clipPath:'inset(0 0 100% 0)',autoAlpha:0,duration:.55,ease:'power3.inOut',onComplete:()=>menuPanel.classList.remove('is-open')});
    }
  }else{
    menuPanel.classList.toggle('is-open',open);
  }
};

menuToggle?.addEventListener('click',()=>setMenu(menuToggle.getAttribute('aria-expanded')!=='true'));
menuPanel?.querySelectorAll('a').forEach(link=>link.addEventListener('click',()=>setMenu(false)));
window.addEventListener('keydown',event=>{
  if(event.key==='Escape'&&menuToggle?.getAttribute('aria-expanded')==='true')setMenu(false);
});

if(finePointer&&!reducedMotion){
  const cursor=document.querySelector('.cursor');
  if(cursor){
    let targetX=window.innerWidth/2,targetY=window.innerHeight/2,currentX=targetX,currentY=targetY;
    window.addEventListener('pointermove',event=>{targetX=event.clientX;targetY=event.clientY},{passive:true});
    const renderCursor=()=>{
      currentX+=(targetX-currentX)*.18;
      currentY+=(targetY-currentY)*.18;
      cursor.style.transform=`translate3d(${currentX}px,${currentY}px,0) translate(-50%,-50%)`;
      window.requestAnimationFrame(renderCursor);
    };
    renderCursor();
    document.querySelectorAll('a,button').forEach(item=>{
      item.addEventListener('pointerenter',()=>cursor.classList.add('is-active'));
      item.addEventListener('pointerleave',()=>cursor.classList.remove('is-active'));
    });
  }

  document.querySelectorAll('.magnetic').forEach(item=>{
    item.addEventListener('pointermove',event=>{
      const box=item.getBoundingClientRect();
      const x=(event.clientX-box.left-box.width/2)*.16;
      const y=(event.clientY-box.top-box.height/2)*.16;
      if(gsap)gsap.to(item,{x,y,duration:.35,ease:'power3.out',overwrite:true});
      else item.style.transform=`translate(${x}px,${y}px)`;
    });
    item.addEventListener('pointerleave',()=>{
      if(gsap)gsap.to(item,{x:0,y:0,duration:.5,ease:'elastic.out(1,.45)',overwrite:true});
      else item.style.transform='';
    });
  });
}

if(gsap&&ScrollTrigger&&!reducedMotion){
  gsap.registerPlugin(ScrollTrigger);
  document.documentElement.classList.add('motion-ready');

  const productStage=document.querySelector('[data-product-stage]');
  const exploded=document.querySelector('[data-exploded]');
  const faceField=document.querySelector('.face-field');
  const serviceObject=document.querySelector('[data-service-object]');
  const grain=document.querySelector('.grain');
  const kineticTargets=[...document.querySelectorAll('.hero-line,.mechanism-heading h2,.sequence-intro h2,.anatomy-copy h2,.service-copy h2')];

  const stageX=productStage?gsap.quickTo(productStage,'x',{duration:.8,ease:'power3.out'}):null;
  const stageY=productStage?gsap.quickTo(productStage,'y',{duration:.8,ease:'power3.out'}):null;
  const stageRX=productStage?gsap.quickTo(productStage,'rotationX',{duration:.9,ease:'power3.out'}):null;
  const stageRY=productStage?gsap.quickTo(productStage,'rotationY',{duration:.9,ease:'power3.out'}):null;
  const explodedRX=exploded?gsap.quickTo(exploded,'rotationX',{duration:.75,ease:'power3.out'}):null;
  const explodedRY=exploded?gsap.quickTo(exploded,'rotationY',{duration:.75,ease:'power3.out'}):null;
  const faceRX=faceField?gsap.quickTo(faceField,'rotationX',{duration:.8,ease:'power3.out'}):null;
  const faceRY=faceField?gsap.quickTo(faceField,'rotationY',{duration:.8,ease:'power3.out'}):null;
  const serviceRX=serviceObject?gsap.quickTo(serviceObject,'rotationX',{duration:.8,ease:'power3.out'}):null;
  const serviceRY=serviceObject?gsap.quickTo(serviceObject,'rotationY',{duration:.8,ease:'power3.out'}):null;
  const kineticSkews=kineticTargets.map(target=>gsap.quickTo(target,'skewX',{duration:.42,ease:'power3.out'}));

  if(finePointer){
    window.addEventListener('pointermove',event=>{
      const nx=(event.clientX/window.innerWidth-.5)*2;
      const ny=(event.clientY/window.innerHeight-.5)*2;
      stageX?.(nx*18); stageY?.(ny*12); stageRX?.(-ny*2.4); stageRY?.(nx*3.8);
      explodedRX?.(-ny*2.1); explodedRY?.(nx*3.4);
      faceRX?.(-ny*2.7); faceRY?.(nx*3.7);
      serviceRX?.(-ny*1.8); serviceRY?.(nx*2.8);
    },{passive:true});
  }

  if(Lenis&&desktop&&finePointer){
    lenisInstance=new Lenis({lerp:0.075,smoothWheel:true,wheelMultiplier:.9,touchMultiplier:1});
    document.documentElement.style.scrollBehavior='auto';
    let velocity=0;
    lenisInstance.on('scroll',event=>{
      ScrollTrigger.update();
      velocity=clamp(-14,14,Number(event.velocity||0));
      document.documentElement.style.setProperty('--scroll-v',velocity.toFixed(3));
      const skew=clamp(-2.4,2.4,velocity*.12);
      kineticSkews.forEach((setter,index)=>setter(index%2?skew:-skew));
      if(grain)grain.style.transform=`translate3d(0,${clamp(-8,8,velocity*.65)}px,0)`;
    });
    gsap.ticker.add(time=>lenisInstance.raf(time*1000));
    gsap.ticker.lagSmoothing(0);

    document.querySelectorAll('a[href^="#"]').forEach(link=>{
      link.addEventListener('click',event=>{
        const href=link.getAttribute('href');
        if(!href||href==='#')return;
        const target=document.querySelector(href);
        if(!target)return;
        event.preventDefault();
        if(menuToggle?.getAttribute('aria-expanded')==='true')setMenu(false);
        lenisInstance.scrollTo(target,{offset:-(header?.offsetHeight||0)+1,duration:1.15});
      });
    });
  }

  const heroTimeline=gsap.timeline({defaults:{ease:'power4.out'}});
  heroTimeline
    .from('.hero-topline',{y:24,opacity:0,duration:.7},.08)
    .from('.hero-line i',{yPercent:112,duration:1.05,stagger:.09},.12)
    .from('.hero-bottom',{y:30,opacity:0,duration:.8},.48)
    .from('[data-product-stage]',{scale:.82,rotationZ:4,opacity:0,duration:1.25,ease:'expo.out'},.12)
    .from('.stage-orbit',{scale:.6,opacity:0,duration:1.4,stagger:.1},.25);

  gsap.to('[data-hero-product]',{
    yPercent:13,rotateY:8,rotateZ:-3,ease:'none',
    scrollTrigger:{trigger:'.hero',start:'top top',end:'bottom top',scrub:1.25}
  });
  gsap.to('.hero-line:nth-child(1)',{xPercent:-5,yPercent:-7,ease:'none',scrollTrigger:{trigger:'.hero',start:'top top',end:'bottom top',scrub:1.4}});
  gsap.to('.hero-line:nth-child(2)',{xPercent:3,yPercent:-13,ease:'none',scrollTrigger:{trigger:'.hero',start:'top top',end:'bottom top',scrub:1.55}});
  gsap.to('.hero-line:nth-child(3)',{xPercent:8,yPercent:-18,ease:'none',scrollTrigger:{trigger:'.hero',start:'top top',end:'bottom top',scrub:1.7}});
  gsap.to('.stage-orbit--one',{rotate:22,scale:1.08,ease:'none',scrollTrigger:{trigger:'.hero',start:'top top',end:'bottom top',scrub:1.5}});
  gsap.to('.stage-orbit--two',{rotate:-38,scale:.94,ease:'none',scrollTrigger:{trigger:'.hero',start:'top top',end:'bottom top',scrub:1.8}});

  const statement=document.querySelector('.statement-copy');
  if(statement){
    const words=statement.textContent.trim().split(/\s+/);
    statement.innerHTML=words.map(word=>`<span class="statement-word">${word}</span>`).join(' ');
    gsap.fromTo('.statement-word',{opacity:.12,y:32,rotationX:-38,transformPerspective:900},{opacity:1,y:0,rotationX:0,stagger:.07,ease:'power2.out',scrollTrigger:{trigger:'.statement',start:'top 72%',end:'bottom 46%',scrub:.7}});
  }

  if(desktop){
    const mechanism=document.querySelector('[data-mechanism]');
    const partElements=[...document.querySelectorAll('[data-exploded] [data-part]')];
    const zDepth=[190,98,18,-84,-175];
    const rotateY=[-17,-9,0,10,18];
    const rotateX=[3.5,2,0,-2,-3.5];
    const settleY=[-7,4,8,1,-5];
    gsap.set(partElements,{transformPerspective:1400,transformOrigin:'50% 50%',force3D:true});
    gsap.set('.part-fluid .fluid-line',{strokeDasharray:'14 10',strokeDashoffset:170});

    const mechanismTl=gsap.timeline({
      scrollTrigger:{trigger:mechanism,start:'top top',end:'bottom bottom',scrub:1.45,fastScrollEnd:false,invalidateOnRefresh:true}
    });
    mechanismTl
      .fromTo('.mechanism-heading',{x:-34,opacity:.7},{x:0,opacity:1,duration:.16},0)
      .to(partElements,{scale:(index)=>1-index*.008,rotationZ:(index)=>index%2?-.8:.8,duration:.08,ease:'power2.inOut',stagger:.012},.02)
      .to(partElements,{
        x:(index,target)=>Number(target.dataset.explodeX||0)*1.08,
        y:(index,target)=>Number(target.dataset.explodeY||0),
        z:(index)=>zDepth[index],
        rotationY:(index)=>rotateY[index],
        rotationX:(index)=>rotateX[index],
        rotationZ:(index,target)=>Number(target.dataset.explodeR||0),
        scale:(index)=>1-index*.012,
        duration:.6,ease:'power3.inOut',stagger:.018
      },.1)
      .to('.part-fluid .fluid-line',{strokeDashoffset:0,opacity:1,duration:.25,ease:'none'},.31)
      .to('.part-core circle',{scale:1.16,transformOrigin:'50% 50%',stagger:.025,duration:.16,ease:'power2.out'},.39)
      .to('.part-core circle',{scale:1,stagger:.025,duration:.17,ease:'power2.inOut'},.51)
      .to('.part-label',{opacity:1,y:4,duration:.22,stagger:.03,ease:'power2.out'},.43)
      .to('.mechanism-progress i',{scaleX:1,duration:.9,ease:'none'},0)
      .fromTo('.explode-axis',{scaleX:.12,opacity:.1},{scaleX:1,opacity:.45,transformOrigin:'center',duration:.5,ease:'power2.inOut'},.14)
      .to(partElements,{y:(index,target)=>Number(target.dataset.explodeY||0)+settleY[index],duration:.16,ease:'sine.inOut',stagger:.02},.8);

    ScrollTrigger.create({
      trigger:mechanism,start:'top top',end:'bottom bottom',
      onUpdate:self=>{
        const v=clamp(-2400,2400,self.getVelocity());
        const target=clamp(-2.2,2.2,v/1050);
        gsap.to('.mechanism-heading h2',{skewX:target,duration:.32,ease:'power3.out',overwrite:true});
      }
    });

    const sequence=document.querySelector('[data-sequence]');
    const track=document.querySelector('[data-sequence-track]');
    if(sequence&&track){
      const horizontalDistance=()=>Math.max(0,track.scrollWidth-(window.innerWidth*.62));
      const horizontalTween=gsap.to(track,{x:()=>-horizontalDistance(),ease:'none',scrollTrigger:{trigger:sequence,start:'top top',end:'bottom bottom',scrub:1.15,invalidateOnRefresh:true}});
      const sequenceFx=gsap.timeline({scrollTrigger:{trigger:sequence,start:'top top',end:'bottom bottom',scrub:1.05}});
      sequenceFx
        .to('.sequence-progress span',{scaleX:1,duration:1,ease:'none'},0)
        .fromTo('.sequence-card',{y:42,rotation:(index)=>index%2?1.25:-1.25},{y:0,rotation:0,duration:.24,stagger:.23,ease:'power2.out'},.02)
        .to('.sequence-card--deliver .drop',{y:120,opacity:.16,stagger:.05,duration:.2,ease:'none'},.12)
        .to('.work-visual span',{scale:.62,rotation:110,stagger:.035,duration:.22,ease:'sine.inOut'},.42)
        .to('.collect-visual span',{scaleX:.34,stagger:.035,duration:.22,ease:'none'},.7)
        .to('.sequence-visual',{rotation:(index)=>index===1?-18:16,duration:.26,stagger:.22,ease:'sine.inOut'},.08);

      gsap.utils.toArray('.sequence-card').forEach((card,index)=>{
        const visual=card.querySelector('.sequence-visual');
        if(!visual)return;
        gsap.fromTo(visual,{xPercent:index%2?-8:8},{xPercent:index%2?8:-8,ease:'none',scrollTrigger:{trigger:card,containerAnimation:horizontalTween,start:'left right',end:'right left',scrub:true}});
      });
    }
  }else{
    gsap.utils.toArray('.sequence-card').forEach((card,index)=>{
      gsap.from(card,{y:54,rotation:index%2?1.3:-1.3,opacity:.55,duration:.7,ease:'power3.out',scrollTrigger:{trigger:card,start:'top 88%',end:'top 58%',scrub:.55}});
      const visual=card.querySelector('.sequence-visual');
      if(visual)gsap.to(visual,{rotation:index===1?-18:14,ease:'none',scrollTrigger:{trigger:card,start:'top bottom',end:'bottom top',scrub:1}});
    });
    gsap.to('.sequence-card--deliver .drop',{y:90,opacity:.2,stagger:.08,ease:'none',scrollTrigger:{trigger:'.sequence-card--deliver',start:'top 70%',end:'bottom 30%',scrub:1}});
    gsap.to('.work-visual span',{scale:.65,rotation:90,stagger:.05,ease:'none',scrollTrigger:{trigger:'.sequence-card--work',start:'top 70%',end:'bottom 30%',scrub:1}});
    gsap.to('.collect-visual span',{scaleX:.38,stagger:.05,ease:'none',scrollTrigger:{trigger:'.sequence-card--collect',start:'top 70%',end:'bottom 30%',scrub:1}});
  }

  const anatomyTl=gsap.timeline({scrollTrigger:{trigger:'[data-anatomy]',start:'top 72%',end:'center 42%',scrub:.85}});
  anatomyTl
    .from('.face-field',{scale:.72,rotationY:-24,rotationX:8,transformPerspective:900,opacity:.38,duration:.7,ease:'power3.out'})
    .from('.face-eye,.face-nose',{scale:.5,opacity:0,duration:.26,stagger:.06},.26)
    .from('.zone-line',{scale:.78,opacity:0,duration:.35,stagger:.06},.35)
    .from('.anatomy-callout',{x:(index)=>index===1?34:-34,opacity:0,duration:.32,stagger:.06},.44)
    .to('.anatomy-visual',{yPercent:-4,duration:.3,ease:'none'},.68);

  gsap.fromTo('[data-service-cartridge]',{x:0,rotation:0},{x:()=>Math.min(260,window.innerWidth*.19),rotation:4,ease:'power2.inOut',scrollTrigger:{trigger:'[data-service]',start:'top 68%',end:'bottom 42%',scrub:1,invalidateOnRefresh:true}});
  gsap.to('[data-service-object]',{yPercent:-5,ease:'none',scrollTrigger:{trigger:'[data-service]',start:'top bottom',end:'bottom top',scrub:1.3}});
  gsap.from('.service-copy > *',{y:30,opacity:0,stagger:.08,duration:.7,ease:'power3.out',scrollTrigger:{trigger:'[data-service]',start:'top 65%'}});

  gsap.utils.toArray('.development-ledger article').forEach((row,index)=>{
    gsap.from(row,{x:index%2?28:-28,opacity:.36,duration:.7,ease:'power3.out',scrollTrigger:{trigger:row,start:'top 84%',end:'top 62%',scrub:.5}});
  });

  gsap.from('.access > *:not(.access-mark)',{y:34,opacity:0,stagger:.07,duration:.7,ease:'power3.out',scrollTrigger:{trigger:'[data-access]',start:'top 65%'}});
  gsap.to('.access-mark',{rotation:7,scale:1.13,ease:'none',scrollTrigger:{trigger:'[data-access]',start:'top bottom',end:'bottom top',scrub:1.2}});

  window.addEventListener('load',()=>ScrollTrigger.refresh(),{once:true});
}else{
  document.documentElement.classList.add('motion-static');
}

import('./cinematic.js').catch(()=>{});
