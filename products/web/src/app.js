const button=document.querySelector('#notify');
const status=document.querySelector('#access-status');
button?.addEventListener('click',()=>{
  button.disabled=true;
  button.textContent='Early access not open';
  if(status)status.textContent='Early access is not open yet. No signup or availability is implied by this preview.';
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

const preloader=document.querySelector('[data-preloader]');
const loaderCount=document.querySelector('[data-loader-count]');
const loaderLine=document.querySelector('[data-loader-line]');
if(preloader&&!reducedMotion){
  if(gsap){
    const state={value:0};
    gsap.timeline({defaults:{ease:'power3.inOut'}})
      .to(state,{value:100,duration:1.05,onUpdate:()=>{if(loaderCount)loaderCount.textContent=String(Math.round(state.value)).padStart(3,'0')}})
      .to(loaderLine,{scaleX:1,duration:.8},0)
      .to('.preloader__count',{yPercent:-8,opacity:.75,duration:.35},.95)
      .to(preloader,{clipPath:'inset(0 0 100% 0)',duration:.82,ease:'power4.inOut',onComplete:()=>preloader.classList.add('is-done')},1.18);
  }else{
    window.setTimeout(()=>preloader.classList.add('is-done'),450);
  }
}else preloader?.classList.add('is-done');

const setMenuHeaderContrast=open=>{
  if(!header)return;
  header.style.color=open?'#edeae3':'';
  header.style.backgroundColor=open?'transparent':'';
  header.style.borderColor=open?'transparent':'';
  if(brandMark)brandMark.style.filter=open?'grayscale(1) brightness(0) invert(1)':'';
};
const setMenu=open=>{
  if(!menuToggle||!menuPanel)return;
  menuToggle.setAttribute('aria-expanded',String(open));
  menuPanel.setAttribute('aria-hidden',String(!open));
  document.body.classList.toggle('menu-open',open);
  setMenuHeaderContrast(open);
  if(open)lenisInstance?.stop();else lenisInstance?.start();
  if(gsap&&!reducedMotion){
    if(open){
      menuPanel.classList.add('is-open');
      gsap.fromTo(menuPanel,{clipPath:'inset(0 0 100% 0)',autoAlpha:0},{clipPath:'inset(0 0 0% 0)',autoAlpha:1,duration:.78,ease:'power4.inOut'});
      gsap.fromTo(menuPanel.querySelectorAll('nav a span'),{yPercent:110,rotationX:-28},{yPercent:0,rotationX:0,duration:.7,stagger:.055,delay:.18,ease:'power3.out'});
    }else gsap.to(menuPanel,{clipPath:'inset(0 0 100% 0)',autoAlpha:0,duration:.58,ease:'power3.inOut',onComplete:()=>menuPanel.classList.remove('is-open')});
  }else menuPanel.classList.toggle('is-open',open);
};
menuToggle?.addEventListener('click',()=>setMenu(menuToggle.getAttribute('aria-expanded')!=='true'));
menuPanel?.querySelectorAll('a').forEach(link=>link.addEventListener('click',()=>setMenu(false)));
window.addEventListener('keydown',event=>{if(event.key==='Escape'&&menuToggle?.getAttribute('aria-expanded')==='true')setMenu(false)});

if(finePointer&&!reducedMotion){
  const cursor=document.querySelector('[data-cursor]');
  const cursorLabel=document.querySelector('[data-cursor-label]');
  if(cursor){
    let tx=window.innerWidth/2,ty=window.innerHeight/2,cx=tx,cy=ty;
    window.addEventListener('pointermove',event=>{tx=event.clientX;ty=event.clientY},{passive:true});
    const loop=()=>{
      cx+=(tx-cx)*.19;cy+=(ty-cy)*.19;
      cursor.style.transform=`translate3d(${cx}px,${cy}px,0) translate(-50%,-50%)`;
      requestAnimationFrame(loop);
    };
    loop();
    document.querySelectorAll('a,button,[data-cursor]').forEach(item=>{
      item.addEventListener('pointerenter',()=>{
        cursor.classList.add('is-active');
        const label=item.getAttribute('data-cursor')||'VIEW';
        if(cursorLabel)cursorLabel.textContent=label;
      });
      item.addEventListener('pointerleave',()=>{
        cursor.classList.remove('is-active');
        if(cursorLabel)cursorLabel.textContent='VIEW';
      });
    });
    document.querySelectorAll('.mechanism,.anatomy').forEach(section=>{
      section.addEventListener('pointerenter',()=>cursor.classList.add('is-dark'));
      section.addEventListener('pointerleave',()=>cursor.classList.remove('is-dark'));
    });
  }

  document.querySelectorAll('.magnetic').forEach(item=>{
    item.addEventListener('pointermove',event=>{
      const box=item.getBoundingClientRect();
      const x=(event.clientX-box.left-box.width/2)*.16;
      const y=(event.clientY-box.top-box.height/2)*.16;
      if(gsap)gsap.to(item,{x,y,duration:.34,ease:'power3.out',overwrite:true});
    });
    item.addEventListener('pointerleave',()=>{if(gsap)gsap.to(item,{x:0,y:0,duration:.5,ease:'elastic.out(1,.45)',overwrite:true})});
  });
}

if(gsap&&ScrollTrigger&&!reducedMotion){
  gsap.registerPlugin(ScrollTrigger);
  document.documentElement.classList.add('motion-ready');

  if(Lenis&&desktop&&finePointer){
    lenisInstance=new Lenis({lerp:0.075,smoothWheel:true,wheelMultiplier:.9,touchMultiplier:1});
    document.documentElement.style.scrollBehavior='auto';
    let velocity=0;
    lenisInstance.on('scroll',event=>{
      ScrollTrigger.update();
      velocity=clamp(-14,14,Number(event.velocity||0));
      document.documentElement.style.setProperty('--scroll-v',velocity.toFixed(3));
      const grain=document.querySelector('.grain');
      if(grain)grain.style.transform=`translate3d(${clamp(-5,5,velocity*.22)}px,${clamp(-7,7,velocity*.55)}px,0)`;
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
        lenisInstance.scrollTo(target,{offset:-(header?.offsetHeight||0)+1,duration:1.18});
      });
    });
  }

  const pageIndex=document.querySelector('[data-page-index]');
  const pageProgress=document.querySelector('[data-page-progress]');
  gsap.to(pageProgress,{scaleY:1,ease:'none',scrollTrigger:{trigger:document.documentElement,start:'top top',end:'bottom bottom',scrub:.25}});
  document.querySelectorAll('[data-section-index]').forEach(section=>{
    ScrollTrigger.create({trigger:section,start:'top center',end:'bottom center',onToggle:self=>{if(self.isActive&&pageIndex)pageIndex.textContent=section.dataset.sectionIndex||'00'}});
  });

  const heroTl=gsap.timeline({defaults:{ease:'power4.out'},delay:1.25});
  heroTl
    .from('.hero-title__line i',{yPercent:112,rotationX:-18,duration:1.15,stagger:.09},0)
    .from('.hero-meta',{y:20,opacity:0,duration:.7,stagger:.08},.22)
    .from('[data-product-stage]',{scale:.72,rotationZ:5,opacity:0,duration:1.35,ease:'expo.out'},.08)
    .from('.specimen-ring',{scale:.55,opacity:0,duration:1.45,stagger:.1},.22)
    .from('.object-label',{opacity:0,x:(index)=>index%2?18:-18,duration:.55,stagger:.06},.62)
    .from('.hero-bottom',{y:28,opacity:0,duration:.75},.7);

  const productStage=document.querySelector('[data-product-stage]');
  const heroProduct=document.querySelector('[data-hero-product]');
  if(finePointer&&productStage&&heroProduct){
    const stageX=gsap.quickTo(productStage,'x',{duration:.9,ease:'power3.out'});
    const stageY=gsap.quickTo(productStage,'y',{duration:.9,ease:'power3.out'});
    const productRX=gsap.quickTo(heroProduct,'rotationX',{duration:.95,ease:'power3.out'});
    const productRY=gsap.quickTo(heroProduct,'rotationY',{duration:.95,ease:'power3.out'});
    window.addEventListener('pointermove',event=>{
      const nx=(event.clientX/window.innerWidth-.5)*2;
      const ny=(event.clientY/window.innerHeight-.5)*2;
      stageX(nx*15);stageY(ny*10);productRX(-ny*3.4);productRY(nx*5.6-11);
    },{passive:true});
  }

  gsap.to('[data-hero-product]',{yPercent:18,scale:.91,rotationY:8,rotationZ:-4,ease:'none',scrollTrigger:{trigger:'[data-hero]',start:'top top',end:'bottom top',scrub:1.25}});
  gsap.to('.hero-word--a',{xPercent:-8,yPercent:-16,ease:'none',scrollTrigger:{trigger:'[data-hero]',start:'top top',end:'bottom top',scrub:1.5}});
  gsap.to('.hero-word--b',{xPercent:9,yPercent:13,ease:'none',scrollTrigger:{trigger:'[data-hero]',start:'top top',end:'bottom top',scrub:1.65}});
  gsap.to('.specimen-ring--a',{rotation:28,scale:1.08,ease:'none',scrollTrigger:{trigger:'[data-hero]',start:'top top',end:'bottom top',scrub:1.45}});
  gsap.to('.specimen-ring--b',{rotation:-44,scale:.93,ease:'none',scrollTrigger:{trigger:'[data-hero]',start:'top top',end:'bottom top',scrub:1.65}});

  const statement=document.querySelector('.statement-copy');
  if(statement){
    const words=statement.textContent.trim().split(/\s+/);
    statement.innerHTML=words.map(word=>`<span class="statement-word">${word}</span>`).join(' ');
    gsap.fromTo('.statement-word',{opacity:.09,y:60,rotationX:-54,transformPerspective:1000},{opacity:1,y:0,rotationX:0,stagger:.065,ease:'power2.out',scrollTrigger:{trigger:'.statement',start:'top 78%',end:'bottom 44%',scrub:.75}});
    gsap.to('.statement-ghost',{xPercent:-14,rotation:-4,ease:'none',scrollTrigger:{trigger:'.statement',start:'top bottom',end:'bottom top',scrub:1.5}});
  }

  if(desktop){
    const mechanism=document.querySelector('[data-mechanism]');
    const parts=[...document.querySelectorAll('[data-exploded] [data-part]')];
    const focusItems=[...document.querySelectorAll('[data-focus]')];
    const zDepth=[210,112,20,-96,-205];
    const rotateY=[-18,-10,0,11,19];
    const rotateX=[4,2.5,0,-2.5,-4];
    let lastFocus=-1;
    gsap.set(parts,{transformPerspective:1500,transformOrigin:'50% 50%',force3D:true});
    gsap.set('.part-fluid .fluid-line',{strokeDashoffset:190});
    const mechanismTl=gsap.timeline({scrollTrigger:{
      trigger:mechanism,start:'top top',end:'bottom bottom',scrub:1.4,invalidateOnRefresh:true,
      onUpdate:self=>{
        const progress=self.progress;
        const next=Math.min(4,Math.max(0,Math.floor(progress*5)));
        if(next!==lastFocus){
          lastFocus=next;
          focusItems.forEach((item,index)=>item.classList.toggle('is-active',index===next));
          parts.forEach((part,index)=>gsap.to(part,{opacity:index===next?1:.42,filter:index===next?'drop-shadow(0 28px 34px rgba(0,0,0,.22))':'drop-shadow(0 14px 20px rgba(0,0,0,.08))',duration:.32,overwrite:true}));
        }
      }
    }});
    mechanismTl
      .fromTo('.mechanism-copy',{x:-42,opacity:.55},{x:0,opacity:1,duration:.18},0)
      .to(parts,{scale:(index)=>1-index*.008,rotationZ:(index)=>index%2?-.7:.7,duration:.08,stagger:.012,ease:'power2.inOut'},.02)
      .to(parts,{
        x:(index,target)=>Number(target.dataset.explodeX||0),
        y:(index,target)=>Number(target.dataset.explodeY||0),
        z:index=>zDepth[index],
        rotationY:index=>rotateY[index],
        rotationX:index=>rotateX[index],
        rotationZ:(index,target)=>Number(target.dataset.explodeR||0),
        scale:index=>1-index*.012,
        duration:.58,stagger:.02,ease:'power3.inOut'
      },.08)
      .to('.part-fluid .fluid-line',{strokeDashoffset:0,duration:.28,ease:'none'},.3)
      .to('.part-core circle',{scale:1.18,transformOrigin:'50% 50%',stagger:.025,duration:.15,ease:'power2.out'},.4)
      .to('.part-core circle',{scale:1,stagger:.025,duration:.16,ease:'power2.inOut'},.52)
      .to('[data-mechanism-progress]',{scaleX:1,duration:1,ease:'none'},0)
      .fromTo('.explode-axis',{scaleX:.12,opacity:.08},{scaleX:1,opacity:1,transformOrigin:'center',duration:.52,ease:'power2.inOut'},.13)
      .to(parts,{y:(index,target)=>Number(target.dataset.explodeY||0)+(index%2?6:-6),duration:.14,stagger:.02,ease:'sine.inOut'},.82)
      .to(parts,{opacity:1,duration:.14},.94);

    ScrollTrigger.create({trigger:mechanism,start:'top top',end:'bottom bottom',onUpdate:self=>{
      const v=clamp(-2400,2400,self.getVelocity());
      gsap.to('.mechanism-copy h2',{skewX:clamp(-2.2,2.2,v/1100),duration:.3,ease:'power3.out',overwrite:true});
    }});

    const sequence=document.querySelector('[data-sequence]');
    const track=document.querySelector('[data-sequence-track]');
    const sequenceProgress=document.querySelector('[data-sequence-progress]');
    if(sequence&&track){
      const distance=()=>Math.max(0,track.scrollWidth-window.innerWidth);
      const horizontalTween=gsap.to(track,{x:()=>-distance(),ease:'none',scrollTrigger:{trigger:sequence,start:'top top',end:'bottom bottom',scrub:1.15,invalidateOnRefresh:true,onUpdate:self=>{if(sequenceProgress)sequenceProgress.style.transform=`scaleX(${self.progress})`}}});
      gsap.utils.toArray('.sequence-panel').forEach((panel,index)=>{
        const word=panel.querySelector('.sequence-panel__word');
        const orbit=panel.querySelector('.flow-orbit');
        if(word)gsap.fromTo(word,{xPercent:10},{xPercent:-10,ease:'none',scrollTrigger:{trigger:panel,containerAnimation:horizontalTween,start:'left right',end:'right left',scrub:true}});
        if(orbit)gsap.fromTo(orbit,{rotation:-12,scale:.82},{rotation:12,scale:1.03,ease:'none',scrollTrigger:{trigger:panel,containerAnimation:horizontalTween,start:'left right',end:'right left',scrub:true}});
        const copy=panel.querySelector('.sequence-copy');
        if(copy)gsap.fromTo(copy,{x:90,opacity:.35},{x:0,opacity:1,ease:'none',scrollTrigger:{trigger:panel,containerAnimation:horizontalTween,start:'left 85%',end:'center 55%',scrub:.7}});
        if(index===0)gsap.to(panel.querySelectorAll('.flow-orbit i'),{y:150,opacity:.16,stagger:.08,ease:'none',scrollTrigger:{trigger:panel,containerAnimation:horizontalTween,start:'left 70%',end:'right 30%',scrub:true}});
        if(index===1)gsap.to(panel.querySelectorAll('.flow-orbit i'),{rotation:135,scale:.62,stagger:.05,ease:'none',scrollTrigger:{trigger:panel,containerAnimation:horizontalTween,start:'left 70%',end:'right 30%',scrub:true}});
        if(index===2)gsap.to(panel.querySelectorAll('.flow-orbit i'),{scaleX:.28,stagger:.05,ease:'none',scrollTrigger:{trigger:panel,containerAnimation:horizontalTween,start:'left 70%',end:'right 30%',scrub:true}});
      });
    }
  }else{
    gsap.utils.toArray('.sequence-panel').forEach((panel,index)=>{
      gsap.from(panel,{y:54,opacity:.55,duration:.75,ease:'power3.out',scrollTrigger:{trigger:panel,start:'top 88%',end:'top 58%',scrub:.55}});
      const orbit=panel.querySelector('.flow-orbit');
      if(orbit)gsap.to(orbit,{rotation:index===1?-18:16,ease:'none',scrollTrigger:{trigger:panel,start:'top bottom',end:'bottom top',scrub:1}});
    });
  }

  const anatomyTl=gsap.timeline({scrollTrigger:{trigger:'[data-anatomy]',start:'top 76%',end:'center 42%',scrub:.9}});
  anatomyTl
    .from('.face-field',{scale:.7,rotationY:-26,rotationX:9,transformPerspective:1000,opacity:.25,duration:.7,ease:'power3.out'})
    .from('.face-halo',{scale:.7,opacity:0,duration:.45},.08)
    .from('.face-eye,.face-nose',{scale:.45,opacity:0,duration:.24,stagger:.06},.26)
    .from('.zone-line',{scale:.75,opacity:0,duration:.34,stagger:.06},.34)
    .from('.anatomy-callout',{x:(index)=>index===1?40:-40,opacity:0,duration:.32,stagger:.06},.42)
    .fromTo('.scan-line',{top:'8%',opacity:0},{top:'88%',opacity:.7,duration:.48,ease:'none'},.46);
  gsap.to('.anatomy-grid',{xPercent:-8,ease:'none',scrollTrigger:{trigger:'[data-anatomy]',start:'top bottom',end:'bottom top',scrub:1.3}});

  if(finePointer){
    const face=document.querySelector('.face-field');
    if(face){
      const rx=gsap.quickTo(face,'rotationX',{duration:.85,ease:'power3.out'});
      const ry=gsap.quickTo(face,'rotationY',{duration:.85,ease:'power3.out'});
      window.addEventListener('pointermove',event=>{const nx=(event.clientX/window.innerWidth-.5)*2;const ny=(event.clientY/window.innerHeight-.5)*2;rx(-ny*3.2);ry(nx*4.4)},{passive:true});
    }
  }

  gsap.fromTo('[data-service-cartridge]',{x:0,rotation:0},{x:()=>Math.min(300,window.innerWidth*.22),rotation:5,ease:'power2.inOut',scrollTrigger:{trigger:'[data-service]',start:'top 72%',end:'bottom 38%',scrub:1.1,invalidateOnRefresh:true}});
  gsap.to('.service-rail i',{x:()=>-Math.min(260,window.innerWidth*.19),ease:'none',scrollTrigger:{trigger:'[data-service]',start:'top 72%',end:'bottom 38%',scrub:1.1,invalidateOnRefresh:true}});
  gsap.to('[data-service-object]',{yPercent:-6,rotationY:5,ease:'none',scrollTrigger:{trigger:'[data-service]',start:'top bottom',end:'bottom top',scrub:1.35}});
  gsap.from('.service-copy > *',{y:32,opacity:0,stagger:.08,duration:.7,ease:'power3.out',scrollTrigger:{trigger:'[data-service]',start:'top 68%'}});

  gsap.utils.toArray('.development-ledger article').forEach((row,index)=>{
    gsap.from(row,{x:index%2?38:-38,opacity:.3,duration:.7,ease:'power3.out',scrollTrigger:{trigger:row,start:'top 86%',end:'top 62%',scrub:.5}});
  });
  gsap.from('.access > *:not(.access-word)',{y:36,opacity:0,stagger:.07,duration:.75,ease:'power3.out',scrollTrigger:{trigger:'[data-access]',start:'top 67%'}});
  gsap.to('.access-word',{rotation:8,scale:1.14,ease:'none',scrollTrigger:{trigger:'[data-access]',start:'top bottom',end:'bottom top',scrub:1.25}});

  if(document.readyState==='complete')ScrollTrigger.refresh();
  else window.addEventListener('load',()=>ScrollTrigger.refresh(),{once:true});
}else document.documentElement.classList.add('motion-static');

import('./cinematic.js').catch(()=>{});