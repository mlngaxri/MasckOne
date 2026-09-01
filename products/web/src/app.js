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

const setHeaderState=()=>header?.classList.toggle('is-scrolled',window.scrollY>24);
setHeaderState();
window.addEventListener('scroll',setHeaderState,{passive:true});

const setMenu=(open)=>{
  if(!menuToggle||!menuPanel)return;
  menuToggle.setAttribute('aria-expanded',String(open));
  menuPanel.setAttribute('aria-hidden',String(!open));
  document.body.classList.toggle('menu-open',open);
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

  if(Lenis&&desktop&&finePointer){
    const lenis=new Lenis({lerp:0.085,smoothWheel:true,wheelMultiplier:.92,touchMultiplier:1});
    lenis.on('scroll',ScrollTrigger.update);
    gsap.ticker.add(time=>lenis.raf(time*1000));
    gsap.ticker.lagSmoothing(0);
  }

  const heroTimeline=gsap.timeline({defaults:{ease:'power4.out'}});
  heroTimeline
    .from('.hero-topline',{y:24,opacity:0,duration:.7},.08)
    .from('.hero-line i',{yPercent:112,duration:1.05,stagger:.09},.12)
    .from('.hero-bottom',{y:30,opacity:0,duration:.8},.48)
    .from('[data-product-stage]',{scale:.82,rotation:4,opacity:0,duration:1.25,ease:'expo.out'},.12)
    .from('.stage-orbit',{scale:.6,opacity:0,duration:1.4,stagger:.1},.25);

  gsap.to('[data-hero-product]',{
    yPercent:13,
    rotateY:8,
    rotateZ:-3,
    ease:'none',
    scrollTrigger:{trigger:'.hero',start:'top top',end:'bottom top',scrub:1.2}
  });
  gsap.to('.stage-orbit--one',{rotate:18,ease:'none',scrollTrigger:{trigger:'.hero',start:'top top',end:'bottom top',scrub:1.5}});
  gsap.to('.stage-orbit--two',{rotate:-34,ease:'none',scrollTrigger:{trigger:'.hero',start:'top top',end:'bottom top',scrub:1.8}});

  const statement=document.querySelector('.statement-copy');
  if(statement){
    const words=statement.textContent.trim().split(/\s+/);
    statement.innerHTML=words.map(word=>`<span class="statement-word">${word}</span>`).join(' ');
    gsap.fromTo('.statement-word',{opacity:.14,y:26},{opacity:1,y:0,stagger:.075,ease:'power2.out',scrollTrigger:{trigger:'.statement',start:'top 70%',end:'bottom 48%',scrub:.65}});
  }

  if(desktop){
    const mechanism=document.querySelector('[data-mechanism]');
    const partElements=[...document.querySelectorAll('[data-exploded] [data-part]')];
    const mechanismTl=gsap.timeline({scrollTrigger:{trigger:mechanism,start:'top top',end:'bottom bottom',scrub:1.15}});
    mechanismTl
      .fromTo('.mechanism-heading',{x:-34,opacity:.7},{x:0,opacity:1,duration:.18},0)
      .to(partElements,{x:(index,target)=>Number(target.dataset.explodeX||0),y:(index,target)=>Number(target.dataset.explodeY||0),rotation:(index,target)=>Number(target.dataset.explodeR||0),duration:.58,ease:'power2.inOut',stagger:.025},.08)
      .to('.part-label',{opacity:1,y:4,duration:.24,stagger:.035},.42)
      .to('.mechanism-progress i',{scaleX:1,duration:.8,ease:'none'},0)
      .to('.explode-axis',{opacity:.42,duration:.2},.2)
      .to(partElements,{y:'-=12',duration:.18,ease:'sine.inOut',stagger:{each:.03,from:'center'}},.77);

    const sequence=document.querySelector('[data-sequence]');
    const track=document.querySelector('[data-sequence-track]');
    if(sequence&&track){
      const horizontalDistance=()=>Math.max(0,track.scrollWidth-(window.innerWidth*0.62));
      gsap.to(track,{x:()=>-horizontalDistance(),ease:'none',scrollTrigger:{trigger:sequence,start:'top top',end:'bottom bottom',scrub:1.05,invalidateOnRefresh:true}});
      gsap.to('.sequence-progress span',{scaleX:1,ease:'none',scrollTrigger:{trigger:sequence,start:'top top',end:'bottom bottom',scrub:true}});
    }
  }

  gsap.utils.toArray('.sequence-card').forEach((card,index)=>{
    const visual=card.querySelector('.sequence-visual');
    gsap.from(card,{y:54,rotation:index%2?1.3:-1.3,opacity:.55,ease:'power2.out',scrollTrigger:{trigger:card,start:'left 92%',end:'left 55%',scrub:.65,horizontal:desktop}});
    if(visual)gsap.to(visual,{rotation:index===1?-22:18,ease:'none',scrollTrigger:{trigger:card,start:desktop?'left right':'top bottom',end:desktop?'right left':'bottom top',scrub:1,horizontal:desktop}});
  });
  gsap.to('.sequence-card--deliver .drop',{y:120,opacity:.16,stagger:.12,ease:'none',scrollTrigger:{trigger:'.sequence-card--deliver',start:desktop?'left 80%':'top 80%',end:desktop?'right 25%':'bottom 30%',scrub:1,horizontal:desktop}});
  gsap.to('.work-visual span',{scale:.62,rotation:110,stagger:.06,ease:'sine.inOut',scrollTrigger:{trigger:'.sequence-card--work',start:desktop?'left 80%':'top 80%',end:desktop?'right 25%':'bottom 30%',scrub:1,horizontal:desktop}});
  gsap.to('.collect-visual span',{scaleX:.34,stagger:.06,ease:'none',scrollTrigger:{trigger:'.sequence-card--collect',start:desktop?'left 80%':'top 80%',end:desktop?'right 25%':'bottom 30%',scrub:1,horizontal:desktop}});

  const anatomyTl=gsap.timeline({scrollTrigger:{trigger:'[data-anatomy]',start:'top 72%',end:'center 42%',scrub:.8}});
  anatomyTl
    .from('.face-field',{scale:.72,rotationY:-24,rotationX:8,transformPerspective:900,opacity:.38,duration:.7,ease:'power3.out'})
    .from('.face-eye,.face-nose',{scale:.5,opacity:0,duration:.26,stagger:.06},.26)
    .from('.zone-line',{scale:.78,opacity:0,duration:.35,stagger:.06},.35)
    .from('.anatomy-callout',{x:(index)=>index===1?34:-34,opacity:0,duration:.32,stagger:.06},.44);

  gsap.fromTo('[data-service-cartridge]',{x:0,rotation:0},{x:()=>Math.min(260,window.innerWidth*.19),rotation:4,ease:'power2.inOut',scrollTrigger:{trigger:'[data-service]',start:'top 68%',end:'bottom 42%',scrub:.9,invalidateOnRefresh:true}});
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
