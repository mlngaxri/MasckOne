const PRODUCT_ASSET_BASE='https://cdn.jsdelivr.net/gh/mlngaxri/MasckOne@0ce6725175f972465efc4cbe0434777a90c10ea4/products/web/public/product';
const MASCK_ASSETS=Object.freeze({hero:`${PRODUCT_ASSET_BASE}/hero.svg`,shell:`${PRODUCT_ASSET_BASE}/shell.svg`,fluid:`${PRODUCT_ASSET_BASE}/fluid.svg`,interface:`${PRODUCT_ASSET_BASE}/interface.svg`,core:`${PRODUCT_ASSET_BASE}/core.svg`,cartridge:`${PRODUCT_ASSET_BASE}/cartridge.svg`});

const clamp=(min,max,value)=>Math.min(max,Math.max(min,value));
const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const desktop=window.matchMedia('(min-width: 861px)').matches;
const q=(selector,root=document)=>root.querySelector(selector);
const qa=(selector,root=document)=>[...root.querySelectorAll(selector)];

const makeImage=(src,className,alt='',priority='auto')=>{
  const image=new Image();
  image.src=src;
  image.alt=alt;
  image.decoding='async';
  image.loading='eager';
  image.fetchPriority=priority;
  image.className=className;
  image.draggable=false;
  return image;
};

const heroProduct=q('[data-hero-product]');
if(heroProduct){
  heroProduct.replaceChildren(makeImage(MASCK_ASSETS.hero,'hero-render','', 'high'));
}

const layerSources={shell:MASCK_ASSETS.shell,fluid:MASCK_ASSETS.fluid,interface:MASCK_ASSETS.interface,core:MASCK_ASSETS.core,cartridge:MASCK_ASSETS.cartridge};
qa('[data-exploded] [data-part]').forEach(part=>{
  const key=part.dataset.part;
  if(!layerSources[key])return;
  part.replaceChildren(makeImage(layerSources[key],`layer-render layer-render--${key}`,''));
});

const interfaceField=q('.face-field');
if(interfaceField){
  const scan=q('.scan-line',interfaceField);
  interfaceField.prepend(makeImage(MASCK_ASSETS.interface,'interface-render',''));
  if(scan)interfaceField.append(scan);
}
const serviceShell=q('.service-shell');
if(serviceShell)serviceShell.replaceChildren(makeImage(MASCK_ASSETS.shell,'service-shell-render',''));
const serviceCartridge=q('[data-service-cartridge]');
if(serviceCartridge)serviceCartridge.replaceChildren(makeImage(MASCK_ASSETS.cartridge,'service-cartridge-render',''));
const objectIteration=q('.object-label--b');
if(objectIteration)objectIteration.textContent='ITERATION 27 / SYSTEM BUILD';

document.documentElement.classList.add('masck-assets-ready');

const allImages=[...qa('.hero-render,.layer-render')];
Promise.allSettled(allImages.map(image=>image.decode?.()||Promise.resolve())).then(()=>{
  document.documentElement.classList.add('masck-images-decoded');
  window.ScrollTrigger?.refresh?.();
});

const exploded=q('[data-exploded]');
const focusItems=qa('[data-focus]');
const parts=qa('[data-exploded] [data-part]');
const partOffsets=[
  {x:-252,y:-20,r:-8,z:180},
  {x:-126,y:18,r:-4,z:92},
  {x:0,y:42,r:0,z:10},
  {x:132,y:8,r:5,z:-82},
  {x:254,y:-22,r:9,z:-155}
];

const setFocus=index=>{
  if(!exploded)return;
  exploded.dataset.layerFocus=String(index);
  focusItems.forEach((item,i)=>item.classList.toggle('is-active',i===index));
};
setFocus(0);

const augmentGsap=()=>{
  const gsap=window.gsap;
  const ScrollTrigger=window.ScrollTrigger;
  if(!gsap||!ScrollTrigger||reduced)return false;
  gsap.registerPlugin(ScrollTrigger);

  const heroRender=q('.hero-render');
  if(heroRender){
    gsap.fromTo(heroRender,{opacity:0,scale:.76,rotationY:-15,rotationZ:4,filter:'blur(10px) drop-shadow(0 0 0 rgba(0,0,0,0))'},{opacity:1,scale:1,rotationY:0,rotationZ:0,filter:'blur(0px) drop-shadow(34px 46px 34px rgba(44,42,39,.19))',duration:1.35,delay:1.28,ease:'expo.out'});
    gsap.to(heroRender,{scale:1.075,rotationZ:-2.2,yPercent:9,ease:'none',scrollTrigger:{trigger:'[data-hero]',start:'top top',end:'bottom top',scrub:1.35}});
  }

  if(exploded&&desktop){
    ScrollTrigger.create({
      trigger:'[data-mechanism]',start:'top top',end:'bottom bottom',
      onUpdate:self=>setFocus(clamp(0,4,Math.floor(self.progress*5)))
    });
    parts.forEach((part,index)=>{
      const image=q('.layer-render',part);
      if(!image)return;
      gsap.to(image,{rotationY:(index-2)*1.8,scale:index===3?.94:1,ease:'none',scrollTrigger:{trigger:'[data-mechanism]',start:'top top',end:'bottom bottom',scrub:1.8}});
    });
  }

  const shine=document.createElement('div');
  shine.className='product-shine';
  q('[data-product-stage]')?.append(shine);
  if(shine){
    Object.assign(shine.style,{position:'absolute',inset:'12% 10%',background:'linear-gradient(108deg,transparent 35%,rgba(255,255,255,.28) 49%,transparent 63%)',transform:'translateX(-95%) skewX(-12deg)',pointerEvents:'none',mixBlendMode:'soft-light',zIndex:'7',borderRadius:'44%'});
    gsap.to(shine,{xPercent:210,ease:'none',scrollTrigger:{trigger:'[data-hero]',start:'top top',end:'bottom 20%',scrub:1.5}});
  }
  return true;
};

const activateNativeFallback=()=>{
  if(reduced)return;
  const root=document.documentElement;
  if(root.classList.contains('masck-native-motion'))return;
  parts.forEach(part=>{part.style.top='50%';part.style.left='50%';part.style.margin='0'});
  root.classList.add('masck-native-motion');
  requestAnimationFrame(()=>requestAnimationFrame(()=>root.classList.add('masck-native-entered')));

  const hero=q('[data-hero]');
  const heroRender=q('.hero-render');
  const mechanism=q('[data-mechanism]');
  const mechanismProgress=q('[data-mechanism-progress]');
  const sequence=q('[data-sequence]');
  const sequenceTrack=q('[data-sequence-track]');
  const sequenceProgress=q('[data-sequence-progress]');
  const anatomy=q('[data-anatomy]');
  const face=q('.face-field');
  const service=q('[data-service]');
  const cartridge=q('[data-service-cartridge]');
  let scheduled=false;

  const render=()=>{
    scheduled=false;
    const vh=window.innerHeight||1;
    if(hero&&heroRender){
      const rect=hero.getBoundingClientRect();
      const p=clamp(0,1,-rect.top/Math.max(1,rect.height));
      heroRender.style.transform=`translate3d(0,${p*52}px,0) scale(${1+p*.075}) rotate(${p*-2.2}deg)`;
      q('.hero-word--a')?.style.setProperty('transform',`translate3d(${-p*5}vw,${-p*5}vh,0)`);
      q('.hero-word--b')?.style.setProperty('transform',`translate3d(${p*5}vw,${p*4}vh,0)`);
    }
    if(mechanism&&exploded&&desktop){
      const rect=mechanism.getBoundingClientRect();
      const travel=Math.max(1,rect.height-vh);
      const p=clamp(0,1,-rect.top/travel);
      const eased=p<.18?0:clamp(0,1,(p-.18)/.62);
      const smooth=eased*eased*(3-2*eased);
      const focus=clamp(0,4,Math.floor(p*5));
      setFocus(focus);
      parts.forEach((part,index)=>{
        const o=partOffsets[index];
        const x=o.x*smooth;
        const y=o.y*smooth;
        const scale=1-(Math.abs(o.z)/180)*.045*smooth;
        part.style.transform=`translate3d(calc(-50% + ${x}px),calc(-50% + ${y}px),${o.z*smooth}px) rotate(${o.r*smooth}deg) scale(${scale})`;
        part.style.opacity=String(p>.22&&index!==focus ? .46 : 1);
      });
      if(mechanismProgress)mechanismProgress.style.transform=`scaleX(${p})`;
    }
    if(sequence&&sequenceTrack&&desktop){
      const rect=sequence.getBoundingClientRect();
      const travel=Math.max(1,rect.height-vh);
      const p=clamp(0,1,-rect.top/travel);
      const distance=Math.max(0,sequenceTrack.scrollWidth-window.innerWidth);
      sequenceTrack.style.transform=`translate3d(${-distance*p}px,0,0)`;
      if(sequenceProgress)sequenceProgress.style.transform=`scaleX(${p})`;
    }
    if(anatomy&&face){
      const rect=anatomy.getBoundingClientRect();
      const p=clamp(0,1,(vh-rect.top)/(vh+rect.height));
      face.style.transform=`perspective(1000px) rotateY(${(p-.5)*8}deg) rotateX(${(.5-p)*4}deg)`;
    }
    if(service&&cartridge){
      const rect=service.getBoundingClientRect();
      const p=clamp(0,1,(vh*.75-rect.top)/Math.max(vh*.8,rect.height*.7));
      cartridge.style.transform=`translate3d(${p*Math.min(300,window.innerWidth*.22)}px,0,0) rotate(${p*5}deg)`;
    }
  };
  const schedule=()=>{if(!scheduled){scheduled=true;requestAnimationFrame(render)}};
  addEventListener('scroll',schedule,{passive:true});
  addEventListener('resize',schedule,{passive:true});
  render();
};

const motionHealth=document.createElement('div');
motionHealth.className='motion-health';
motionHealth.textContent='motion fallback';
document.body.append(motionHealth);

const boot=()=>{
  const gsapHealthy=Boolean(window.gsap&&window.ScrollTrigger&&document.documentElement.classList.contains('motion-ready')&&(window.ScrollTrigger.getAll?.().length||0)>3);
  if(gsapHealthy){
    augmentGsap();
    motionHealth.remove();
  }else{
    activateNativeFallback();
    motionHealth.dataset.visible='false';
  }
};

if(document.readyState==='complete')setTimeout(boot,180);
else addEventListener('load',()=>setTimeout(boot,180),{once:true});
